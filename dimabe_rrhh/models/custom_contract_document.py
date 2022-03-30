from odoo import models, fields

class CustomContractDocument(models.Model):
    _name = 'custom.contract.document'
    _description = 'Documentos del Contrato'

    name = fields.Char('Número Documento')

    document_type_id = fields.Many2one('custom.contract.document.type', 'Tipo de Documento')

    document_data = fields.Binary('Archivo')

    document_init_date = fields.Date('Fecha Vigencia')

    document_end_date = fields.Date('Fecha Vencimiento')

    contract_id = fields.Many2one('hr.contract', 'Contrato')