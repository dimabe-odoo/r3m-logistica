from odoo import fields, models, api
from datetime import date


class ConfirmDoneLoan(models.TransientModel):
    _name = 'confirm.done.loan'

    loan_id = fields.Many2one('custom.loan')

    def done(self):
        self.loan_id.write({
            'state': 'done'
        })