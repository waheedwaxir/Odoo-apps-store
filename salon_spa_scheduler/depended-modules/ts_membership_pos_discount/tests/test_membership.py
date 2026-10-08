from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestMembership(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan = cls.env['ts.membership.plan'].create({
            'name': 'Gold', 'discount_percentage': 30.0, 'min_spend': 300.0,
            'duration_months': 12,
        })
        cls.partner = cls.env['res.partner'].create({'name': 'Member'})
        cls.Membership = cls.env['ts.membership']

    def test_offer_for_active_member(self):
        self.Membership.create({'partner_id': self.partner.id, 'plan_id': self.plan.id})
        res = self.Membership.get_pos_member_discount(self.partner.id)
        self.assertEqual(res['discount'], 30.0)
        self.assertEqual(res['min_spend'], 300.0)
        self.assertEqual(res['name'], 'Gold')
        self.assertTrue(res['discount_product_id'])

    def test_no_offer_without_membership(self):
        res = self.Membership.get_pos_member_discount(self.partner.id)
        self.assertEqual(res['discount'], 0.0)
        self.assertTrue(res['discount_product_id'])
        self.assertEqual(self.Membership.get_pos_member_discount(False)['discount'], 0.0)

    def test_cancelled_and_expired_get_no_offer(self):
        m = self.Membership.create({'partner_id': self.partner.id, 'plan_id': self.plan.id})
        m.state = 'cancelled'
        self.assertEqual(self.Membership.get_pos_member_discount(self.partner.id)['discount'], 0.0)
        m.write({'state': 'active', 'end_date': fields.Date.today() - timedelta(days=1)})
        self.assertEqual(self.Membership.get_pos_member_discount(self.partner.id)['discount'], 0.0)

    def test_best_plan_wins(self):
        silver = self.env['ts.membership.plan'].create({'name': 'Silver', 'discount_percentage': 10.0})
        self.Membership.create({'partner_id': self.partner.id, 'plan_id': silver.id})
        self.Membership.create({'partner_id': self.partner.id, 'plan_id': self.plan.id})
        self.assertEqual(self.Membership.get_pos_member_discount(self.partner.id)['name'], 'Gold')

    def test_end_date_and_cron(self):
        m = self.Membership.create({
            'partner_id': self.partner.id, 'plan_id': self.plan.id,
            'start_date': fields.Date.today() - timedelta(days=800)})
        self.assertTrue(m.end_date)
        self.Membership._cron_expire_memberships()
        self.assertEqual(m.state, 'expired')

    def test_partner_summary(self):
        self.Membership.create({'partner_id': self.partner.id, 'plan_id': self.plan.id})
        self.assertEqual(self.partner.ts_membership_summary, 'Gold')
