from odoo import _, api, fields, models


def phone_match_key(number):
    """The last eight digits of a number, or '' when it has fewer than seven.

    Eight digits is a Qatari number without its country code, so
    '+974 3023 6826', '97430236826' and '30236826' come out the same.
    """
    digits = ''.join(ch for ch in (number or '') if ch.isdigit())
    return digits[-8:] if len(digits) >= 7 else ''


def split_phones(value):
    return [part.strip() for part in (value or '').replace(';', ',').split(',') if part.strip()]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    salon_allergies = fields.Text(string='Allergy Information', help="Customer's allergies or medical conditions.")
    salon_preferences = fields.Text(string='Customer Preferences', help="Customer's preferences or special requests.")
    salon_favorite_staff_id = fields.Many2one('salon.staff', string='Favorite Beautician', help="The customer's preferred beautician/staff member.")
    salon_membership_number = fields.Char(
        string='Membership Number', index=True,
        help="Corporate ID the customer shows to claim their scheme discount - "
             "an employee number at Qatar Airways, Qatar University, Hamad Hospital "
             "and so on. Carried over from the previous system.")
    salon_first_visit_date = fields.Date(
        string='First Visit', help="Carried over from the previous system.")
    salon_other_phones = fields.Char(
        string='Other Phones', index='trigram',
        help="Every further number the customer is known by - home, work, a "
             "second mobile. Customer search on the scheduler and in Contacts "
             "looks here as well as in Phone.")
    salon_phone_search = fields.Char(
        string='Any Phone', compute='_compute_salon_phone_search', store=True,
        index='trigram',
        help="Digits of Phone and Other Phones, for searching: '30236826' finds a "
             "number saved as '+974 3023 6826'.")
    salon_duplicate_key = fields.Char(
        string='Possible Duplicate', index=True, copy=False, readonly=True,
        help="Set by Find Duplicate Customers: customers sharing this value have "
             "a phone number in common. Cleared on the next search.")
    customer_history_ids = fields.One2many('salon.customer.history', 'partner_id', string='Service History', help="The customer's complete past service history logs.")
    salon_note_ids = fields.One2many(
        'salon.customer.note', 'partner_id', string='Note History',
        help="Dated log of every Allergies/Preferences save - what was recorded and when.")
    salon_comment_ids = fields.One2many(
        'salon.customer.note', 'partner_id', string='Comments',
        domain=[('comment', '!=', False)],
        help="Comments staff wrote about the customer - rude, a complaint, did "
             "not pay. They show with the General Notes.")

    def action_update_salon_notes(self, allergies, preferences):
        """Overwrite the current Allergies/Preferences snapshot. The note
        history entry is written by write() when something changed."""
        self.ensure_one()
        self.write({'salon_allergies': allergies or False,
                    'salon_preferences': preferences or False})

    def _salon_general_notes_text(self, max_comments=5):
        """Allergies, preferences and the latest comments as one text, for
        the General Notes popup and the scheduler's red sign. Empty when there
        is nothing to read."""
        self.ensure_one()
        parts = []
        if self.salon_allergies:
            parts.append(_("Allergies / Medical Notes:\n%s", self.salon_allergies))
        if self.salon_preferences:
            parts.append(_("Preferences / Styling Notes:\n%s", self.salon_preferences))
        comments = self.salon_comment_ids[:max_comments]
        if comments:
            types = dict(self.env['salon.customer.note']._fields['comment_type']._description_selection(self.env))
            lines = []
            for note in comments:
                head = fields.Date.to_string(fields.Datetime.context_timestamp(self, note.date).date())
                if note.comment_type:
                    head += " - " + types[note.comment_type]
                lines.append("%s: %s" % (head, note.comment))
            if len(self.salon_comment_ids) > max_comments:
                lines.append(_("... and %s older comments on the customer.",
                               len(self.salon_comment_ids) - max_comments))
            parts.append(_("Comments:\n%s", "\n".join(lines)))
        return "\n\n".join(parts)

    def write(self, vals):
        """Every change to Allergies / Preferences - from the customer form,
        the scheduler or a booking - appends a dated entry to the note history
        so past wording isn't lost the next time someone edits it."""
        if self.env.context.get('salon_note_no_log') or not (
                {'salon_allergies', 'salon_preferences'} & set(vals)):
            return super().write(vals)
        before = {p.id: (p.salon_allergies or False, p.salon_preferences or False) for p in self}
        res = super().write(vals)
        notes = [{
            'partner_id': p.id,
            'allergies': p.salon_allergies,
            'preferences': p.salon_preferences,
        } for p in self
            if (p.salon_allergies or False, p.salon_preferences or False) != before[p.id]]
        if notes:
            self.env['salon.customer.note'].sudo().with_context(salon_note_from_partner=True).create(notes)
        return res
    salon_membership_line_ids = fields.One2many('salon.membership.line', 'partner_id', string='Customer Memberships', help="Membership plans this customer is enrolled in.")
    salon_membership_summary = fields.Char(
        string='Memberships', compute='_compute_salon_membership_summary',
        help="Comma-separated list of the membership plans this customer holds.")

    @api.depends('phone', 'salon_other_phones')
    def _compute_salon_phone_search(self):
        for partner in self:
            numbers = [partner.phone] + split_phones(partner.salon_other_phones)
            digits = [''.join(ch for ch in (n or '') if ch.isdigit()) for n in numbers]
            partner.salon_phone_search = ' '.join(dict.fromkeys(d for d in digits if d)) or False

    @api.depends('salon_membership_line_ids.membership_id')
    def _compute_salon_membership_summary(self):
        for partner in self:
            names = partner.salon_membership_line_ids.membership_id.mapped('name')
            partner.salon_membership_summary = ', '.join(sorted(set(filter(None, names))))

    @api.model
    def name_search(self, name='', domain=None, operator='ilike', limit=100):
        if name and not operator.startswith('^'):
            search_fields = []
            if 'phone' in self._fields:
                search_fields.append(('phone', operator, name))
            if 'mobile' in self._fields:
                search_fields.append(('mobile', operator, name))
            search_fields.append(('salon_other_phones', operator, name))
            digits = ''.join(ch for ch in name if ch.isdigit())
            if len(digits) >= 5:
                search_fields.append(('salon_phone_search', 'ilike', digits))

            if search_fields:
                phone_domain = ['|'] * (len(search_fields) - 1) + search_fields
                partners = self.search(phone_domain + (domain or []), limit=limit)
                if partners:
                    return [(p.id, p.display_name) for p in partners]
        return super().name_search(name=name, domain=domain, operator=operator, limit=limit)

    # ------------------------------------------------------------------
    # Duplicate customers
    # ------------------------------------------------------------------
    def _salon_phone_keys(self):
        self.ensure_one()
        keys = {phone_match_key(n) for n in [self.phone] + split_phones(self.salon_other_phones)}
        keys.discard('')
        return keys

    @api.model
    def action_find_salon_duplicates(self):
        """Group customers that share a phone number and open them for review.

        A shared number is the one signal worth acting on: the same name alone
        is mostly different people (six different "Aisha"s), and a shared
        number can still be two people - a sister booking for her sister - so
        nothing is merged here. Tick the ones that are one person and use
        Action > Merge.
        """
        customers = self.search([('customer_rank', '>', 0), ('is_company', '=', False)])
        # Union-find over "has a number in common".
        parent = {}

        def find(pid):
            while parent[pid] != pid:
                parent[pid] = parent[parent[pid]]
                pid = parent[pid]
            return pid

        owner_of_key = {}
        for partner in customers:
            parent.setdefault(partner.id, partner.id)
            for key in partner._salon_phone_keys():
                if key in owner_of_key:
                    parent[find(partner.id)] = find(owner_of_key[key])
                else:
                    owner_of_key[key] = partner.id
        groups = {}
        for pid in parent:
            groups.setdefault(find(pid), []).append(pid)

        self.search([('salon_duplicate_key', '!=', False)]).write({'salon_duplicate_key': False})
        found = 0
        for members in groups.values():
            if len(members) < 2:
                continue
            records = self.browse(members)
            label = ' / '.join(sorted({k for p in records for k in p._salon_phone_keys()}))
            records.write({'salon_duplicate_key': label})
            found += 1
        return {
            'type': 'ir.actions.act_window',
            'name': _('Possible Duplicates (%s groups)', found),
            'res_model': 'res.partner',
            'views': [(False, 'list'), (False, 'form')],
            'domain': [('salon_duplicate_key', '!=', False)],
            'context': {'group_by': 'salon_duplicate_key', 'create': False},
            'help': _('<p class="o_view_nocontent_smiling_face">No duplicates found</p>'
                      '<p>No two customers share a phone number.</p>'),
        }
