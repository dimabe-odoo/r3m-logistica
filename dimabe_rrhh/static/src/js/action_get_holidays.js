odoo.define('custom_holidays.get_holidays_by_year',function (require) {
    let core = require('web.core');
    let ListController = require('web.ListController');
    let rpc = require('web.rpc');
    let session = require('web.session');
    let _t = core._t;
    ListController.include({
        renderButtons: function ($node) {
            this._super.apply(this,arguments);
            if(this.$buttons){
                this.$buttons.find('#getholidays').click(this.proxy('action_get_holidays'));
            }
        },
        action_get_holidays: function () {
            let self = this;
            let user = session.uid;
            rpc.query({
                model: 'custom.holidays',
                method: 'get_holidays_by_year',
                args: [{'id': user}],
            })
        }
    })
})