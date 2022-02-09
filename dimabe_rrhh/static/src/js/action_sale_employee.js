odoo.define('custom_sale_employee.get_sale_employee',function (require) {
    let core = require('web.core');
    let ListController = require('web.ListController');
    let rpc = require('web.rpc');
    let session = require('web.session');
    let _t = core._t;
    ListController.include({
        renderButtons: function ($node) {
            this._super.apply(this,arguments);
            if(this.$buttons){
                this.$buttons.find('#getsaleemployee').click(this.proxy('action_get_sale_employee'));
            }
        },
        action_get_sale_employee: function () {
            let self = this;
            let user = session.uid;
            rpc.query({
                model: 'custom.sale_employee',
                method: 'get_sale_employee',
                args: [{'id': user}],
            })
        }
    })
})