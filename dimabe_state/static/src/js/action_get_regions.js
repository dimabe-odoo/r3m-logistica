odoo.define('custom_region.get_regions', function (require) {
    let core = require('web.core');
    let ListController = require('web.ListController');
    let rpc = require('web.rpc');
    let session = require('web.session');
    let _t = core._t;
    ListController.include({
        renderButtons: function ($node) {
            this._super.apply(this, arguments);
            if (this.$buttons) {
                this.$buttons.find('#get_regions').click(this.proxy('action_get_regions'));
                this.$buttons.find('#get_province').click(this.proxy('action_get_province'));
                this.$buttons.find('#get_commune').click(this.proxy('action_get_commune'));
            }
        },
        action_get_regions: function () {
            let self = this;
            console.log(self);
            let user = session.uid;
            rpc.query({
                model: 'custom.region',
                method: 'get_regions',
                args: [{'id': user}],
            }).then(function (result) {
                self.trigger_up('reload');
            })
        },
        action_get_province: function () {
            let self = this;
            console.log(self);
            let user = session.uid;
            rpc.query({
                model: 'custom.province',
                method: 'get_provinces',
                args: [{'id': user}],
            }).then(function (result) {
                self.trigger_up('reload');
            })
        },
        action_get_commune: function () {
            let self = this;
            console.log(self);
            let user = session.uid;
            rpc.query({
                model: 'custom.commune',
                method: 'get_communes',
                args: [{'id': user}],
            }).then(function (result) {
                self.trigger_up('reload');
            })
        },
    })
})