$(function() {
    if ($("#sidebar").length){
	$("#sidebar > ul").kendoPanelBar().css({ width: 210 })
	    .data("kendoPanelBar").expand($("#sidebar > ul .active_menu").parents('li'));
    };

    var currentM2O = [];

    var m2oChange = function(id) {
	$parent = currentM2O[currentM2O.length-1].parents('.m2o_field');
	$parent.find('input:hidden').val(id);
	var url = $parent.attr('get_name');
	$.getJSON(url.replace('/0/', '/' + id + '/'), {}, function(data){
	    $parent.find('input.m2o_title').val(data.name);
	});
	$parent.find('a').show();
    };

    var gridChange = function(el, type) {
	if (type=='m2o') {
	    m2oChange(el.attr('rowId'));
	    el.parents('.window').data('kendoWindow').close();
	};
    };

    var formInit = function(form, type){
	form = form || $('body');
	form.find(".form_notebook li:first").addClass("k-state-active");
	form.find(".form_notebook").kendoTabStrip();
	form.find(".date_widget").kendoDatePicker({format:'yyyy-MM-dd'});

	form.find('div.edit_form > form').submit(function(){
	    var submit_form = this;
	    $.post($(this).attr('action'), $(this).serialize(),
		   function(data) {
		       console.log(1111111);
		       if (data.href) {
			   if (type == 'm2o') {
			       m2oChange(data.id);
			       form.parents('.window').data('kendoWindow').close();
			   } else {
			       window.location.href = data.href;
			   }
		       }
		       if (data.errors) {
			   form.find('.error-field').removeClass('.error_field');
			   alert_mess = '';
			   for (k in data.errors) {
			       alert_mess += data.errors[k];
			       $(submit_form[k]).addClass('.error_field');
			   };
			   var dialogError = $('<div class="errorsDialog"/>').append(alert_mess);
			   $('body').append(dialogError);
			   dialogError.kendoWindow({'width':'50%',
						    'height':'50%'});
			   dialogError.data('kendoWindow').center();
		       }
		   }
		   , 'json');
	    return false;
	});
	form.find(".tree-grid").each(function(){
	    //return;
	    $this = $(this);
	    var stat = $this.attr('static');
	    if (!stat) {
		var remoteUrl = $this.attr('url');
		var ds = new kendo.data.DataSource({
		    transport: {
			read: { 
			    url: remoteUrl,
			    dataType: "json"
			}
		    },
		    schema: {data:'data', total:'total'},
		    pageSize: 20,
		    serverPaging: true,
		    serverSorting: true
		});
		opts = {
		    dataSource: ds,
		    scrollable: false,
		    sortable: {
			mode: 'multiple',
			allowUnsort: true
		    },
		    selectable: 'multiple row',
		    navigatable: true,
		    pageable: true,
		    change: function(){gridChange(this.select(), type)},
		    rowTemplate: kendo.template($this.prev().html())
		};
	    } else {
		opts = {};
	    }

	    $this.kendoGrid(opts);

	    var per_page = $('<select><option value="20">20</option><option value="50">50</option><option value="100">100</option></select>')
		.css({float:"right",
		      width:"100px"})
		.change(function(){
		    ds.options.pageSize = $(this).val();
		    ds._pageSize = $(this).val();
		    ds._take = $(this).val();
		    ds.read();
		    console.log(ds);
		    $this.data('kendoGrid').refresh();
		});
	    $this.next('.k-grid-pager').append(per_page);
	    per_page.kendoDropDownList();
	});
    }
    var windowCount = 0;

    $(".m2o_field a").live("click", function(){
	var $this = $(this);
	currentM2O.push($this);

	$parent = $(this).parent();
	var url = $this.attr('href').replace('/0/', '/' + $parent.find('input:hidden').val() + '/');
	windowCount++
	var window = $('<div class="window"/>');
	//window.css({'top':'10%', 'left':'5%'})
	$('body').append(window);
	window.kendoWindow({
            width: "90%",
            height: "90%",
            title: $parent.find('.m2o_title').val(),
            content: url,
	    modal: true,
	    refresh: function(){formInit(this.wrapper, 'm2o')},
	    
            close: function(){windowCount--; currentM2O.pop()}
        });
	window.data("kendoWindow").center();
	var wrapp = window.data("kendoWindow").wrapper;
	wrapp.css({'left': parseInt(wrapp.css('left')) * (1-.1*windowCount),
		   'top': parseInt(wrapp.css('top')) *  (1-.1*windowCount),
		  });
	return false;
    });

    formInit();




});