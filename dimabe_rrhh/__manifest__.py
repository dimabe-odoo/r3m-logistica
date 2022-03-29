# -*- coding: utf-8 -*-
{
    'name': "RRHH",

    'summary': """
        Funcionalidades de RRHH adaptados a la ley chilena 
        """,

    'description': """
        Long description of module's purpose
    """,

    'author': "Dimabe Ltda",
    'website': "http://www.dimabe.cl",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','hr','hr_payroll', 'resource','l10n_cl_edi','l10n_cl_edi_boletas', 'hr_holidays', 'hr_holidays_gantt', 'hr_payroll_account'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'data/custom_data_demo.xml',
        'data/custom_data_apv.xml',
        'data/custom_data_afp.xml',
        'data/custom_data_ccaf.xml',
        'data/custom_data_hr_payslip.xml',
        'data/custom_data_mutuality.xml',
        'data/custom_data_contract_type.xml',
        'data/custom_data_section.xml',
        'data/hr_payslip_input_type.xml',
        'data/custom_employee_type.xml',
        'data/custom_isapre.xml',
        'data/hr_action_server.xml',
        'views/hr_contract.xml',
        'views/hr_salary_rule.xml',
        'views/hr_payslip.xml',
        'views/templates.xml',
        'views/wizard_hr_payslip.xml',
        'views/hr_department.xml',
        'views/hr_employee.xml',
        'views/custom_indicators.xml',
        'views/custom_benefits_rrhh.xml',
        'views/custom_data.xml',
        'report/report_payslip.xml',
        'report/report_loan.xml',
        'views/resource_calendar.xml',
        'views/res_company.xml',
        'views/custom_loan.xml',
        'views/confirm_loan.xml',
        'views/custom_holidays.xml',
        'views/main_data_change_report.xml',
        'views/custom_sale_employee.xml',
        'views/custom_vacation.xml',
        'views/hr_leave_type.xml',
        'views/custom_payslip_overdraft.xml',
        'views/custom_confirm_undo_payslip.xml',
        'views/hr_payslip_employee.xml',
        'views/hr_leave_allocation.xml',
        'report/report_vacation.xml',
        'views/hr_leave.xml',
        'views/account_move.xml',
        'data/ir_cron_update_vacations_lines_.xml',
        'views/custom_settlement.xml',
        'data/custom_data_fired_cause.xml',
        'views/custom_fired.xml',
        'report/report_settlement.xml',
        'views/hr_payslip_input_type.xml'
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
    'qweb': [
        'static/src/xml/get_holidays_button.xml',
        'static/src/xml/get_sale_employee.xml'
    ]
}
