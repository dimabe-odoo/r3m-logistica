from odoo import api, fields, models

class CustomSaleEmployee(models.Model):

    _name = 'custom.sale_employee'
    _description = 'Ventas Internas'
    _rec_name = 'reference'

    employee_id = fields.Many2one('hr.employee', 'Empleado', required=True)

    invoice_id = fields.Many2one('account.move', 'Número', required=True)

    invoice_type = fields.Many2one('l10n_latam.document.type','Tipo Documento', related="invoice_id.l10n_latam_document_type_id")

    invoice_date = fields.Date('Fecha', related="invoice_id.date")

    currency_id = fields.Many2one('res.currency', related="invoice_id.currency_id")

    amount_total = fields.Monetary('Monto Total', related="invoice_id.amount_total")

    amount_residual = fields.Monetary('Total Adeudado', related="invoice_id.amount_residual")

    payslip_id = fields.Many2one('hr.payslip', 'Nómina')

    move_id = fields.Many2one('account.move', 'Asiento Contable')

    state = fields.Selection([('to_pay', 'Por Pagar'), ('paid_out', 'Pagado')], default='to_pay', string="Estado", compute="_compute_state", store=True)

    reference = fields.Char('Referencia', compute="_compute_reference")

    @api.depends('invoice_id.amount_residual')
    def _compute_state(self):
        for item in self:
            if item.amount_residual == 0:
                item.state = 'paid_out'
            else:
                item.state = 'to_pay'


    def get_sale_employee(self):
        partner_address_employee_ids = self.env['hr.employee'].search([]).mapped('address_home_id')
        partner_user_employee_ids = self.env['hr.employee'].search([]).mapped('user_id').mapped('partner_id')
        invoice_sale_employee_ids = self.env['custom.sale_employee'].search([]).mapped('invoice_id')

        partner_ids = []
        for address_partner in partner_address_employee_ids:
            if address_partner.id not in partner_ids:
                partner_ids.append(address_partner.id)

        for user_partner in partner_user_employee_ids:
            if user_partner.id not in partner_ids:
                partner_ids.append(user_partner.id)

        invoice_ids = self.env['account.move'].search([('move_type', 'in', ['out_invoice','out_refund']),('state', '=', 'posted'), ('partner_id', 'in', partner_ids), ('id', 'not in', invoice_sale_employee_ids.ids)])

        if len(invoice_ids) > 0:
            for invoice in invoice_ids:
                employee_id = invoice.partner_employee(invoice.partner_id.id)
                if employee_id:
                    self.env['custom.sale_employee'].create({
                        'employee_id': employee_id.id,
                        'invoice_id': invoice.id
                    })

    @api.depends('employee_id','invoice_id')
    def _compute_reference(self):
        for item in self:
            item.reference = f'{item.employee_id.name} - {item.invoice_id.name}'