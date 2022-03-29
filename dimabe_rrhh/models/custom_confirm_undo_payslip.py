from odoo import fields, models, api

class CustomConfirmPayslip(models.TransientModel):
    _name = 'custom.confirm_payslip'
    _description = "Confirmar Nomina por Indicador"

    indicator_id = fields.Many2one('custom.indicators', string="Indicador")

    company_id = fields.Many2one('res.partner', domain=lambda self: [
        ('id', 'in', self.env['hr.employee'].sudo().search([('active', '=', True)]).mapped('address_id').mapped('id'))])

    def confirm_payslips(self):
        payslip_ids = self.env['hr.payslip'].search([('indicator_id','=',self.indicator_id.id)])

        if any(payslip.move_id for payslip in payslip_ids):
            raise models.ValidationError(f'No se puede confirmar Nominas de {self.indicator_id.name}\nExiste un Asiento contable asociado.')

        if any(payslip.state != 'verify' for payslip in payslip_ids):
            raise models.ValidationError(f'No se puede confirmar Nominas de {self.indicator_id.name}\nTodas las Nóminas tienen que estar con estado En Espera.')

        payslip_ids.action_payslip_done()

        #verificar sino es redundante
        for payslip in payslip_ids:
            if payslip.loan_ids:
                for loan in payslip.loan_ids:
                    payslip.write({
                        'fee_id': loan.next_fee_id.id,
                    })
                    loan.next_fee_id.write({
                        'paid': True,
                    })
                    if loan.verify_is_complete():
                        loan.write({
                            'state': 'done'
                        })


class CustomConfirmPayslip(models.TransientModel):
    _name = 'custom.undo_payslip'

    indicator_id = fields.Many2one('custom.indicators', string="Indicador")

    company_id = fields.Many2one('res.partner', domain=lambda self: [
        ('id', 'in', self.env['hr.employee'].sudo().search([('active', '=', True)]).mapped('address_id').mapped('id'))])

    def undo_payslips(self):
        payslip_ids = self.env['hr.payslip'].search([('indicator_id', '=', self.indicator_id.id)])

        move_id = payslip_ids.mapped('move_id')[0]

        if any(payslip.state != 'done' for payslip in payslip_ids):
            raise models.ValidationError(
                f'No se puede deshacer confirmación de Nominas de {self.indicator_id.name}\nTodas las Nóminas tienen que estar con estado Hecho.')

        for payslip in payslip_ids:
            payslip.write({
                'state': 'verify',
                'move_id': None,
                'was_payslip_undded': True
            })

        if move_id:
            try:
                if move_id.state == 'posted':
                    move_id.button_draft()
                move_id.unlink()
            except Exception as e:
                raise models.ValidationError(e)