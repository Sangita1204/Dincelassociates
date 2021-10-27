openerp.dincelaccount = function (instance) {
    instance.web.list.columns.add('field.dcs_color', 'instance.dincelaccount.dcs_color');
    instance.dincelaccount.dcs_color = instance.web.list.Column.extend({
        _format: function (row_data, options) {
            res = this._super.apply(this, arguments);
            //#var amount = parseFloat(res);
            //if (amount < 0){
             return "<font color='"+res+"'>"+(res)+"</font>";
            //}
            //return res
        }
    });
    //
    //here you can add more widgets if you need, as above...
    //
};