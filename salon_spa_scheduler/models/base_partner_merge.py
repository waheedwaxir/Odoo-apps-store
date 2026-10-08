# -*- coding: utf-8 -*-
from odoo import models

from .res_partner import phone_match_key, split_phones


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    def _update_values(self, src_partners, dst_partner):
        """Keep every number when customers are merged.

        The standard merge keeps one value per field - the destination's Phone
        and Other Phones win and the others' numbers are lost. Collect them
        all first and put the ones the merged customer does not have yet
        into Other Phones. Duplicate markers are cleared as well.
        """
        numbers = []
        for partner in [dst_partner, *src_partners]:
            numbers += [partner.phone] + split_phones(partner.salon_other_phones)
        super()._update_values(src_partners, dst_partner)
        seen = {phone_match_key(dst_partner.phone)} - {''}
        others = []
        for number in numbers:
            key = phone_match_key(number)
            if number and key and key not in seen:
                seen.add(key)
                others.append(number.strip())
        dst_partner.write({
            'salon_other_phones': ', '.join(others) or False,
            'salon_duplicate_key': False,
        })
