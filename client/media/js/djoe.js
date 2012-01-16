$(function() {

    var Djoe = function() {
	this.m2oPool = [];
	this.windowCount = 0;
	this.view = {};
	this.menuId = null;
	this.hashState = {};
    };
    Djoe.prototype.PER_PAGES = [20, 50, 100]

    Djoe.prototype.ajaxErrorSetup = function() {
	this.errDialog = $('<div id="errorDialog"/>');
	$('body').append(this.errDialog);
	this.errDialog.css({'visibility': 'hide',
		       'max-width': .85 * $(window).width(),
		       'max-height': .85 * $(window).height(),
		       'border': '1px solid red',
		       'background':'#faa'});
	this.errDialog.kendoWindow({
	    modal: true,
	    visible: false,
	    close: function(){console.log(this); this.element.html('')}
	});

	this.errDialog.ajaxError(function(event, request, settings) {
	    var mess = request.responseText;
	    if (mess.charAt(0) == '{') {
		json = $.parseJSON(mess);
		if (request.status == 403)
		    location.href = json._redirect
		else
		    mess = json.error;
	    } else
		mess = $('<div/>').html(mess);
	    $(this).html(mess)
		.css({visibility: 'show'});
	    $(this).data('kendoWindow').title(request.status + ' : ' + request.statusText)
		.center()
		.open();
	});
    }

    Djoe.prototype.setGlobalEvents = function() {
	var self = this;
	// location.hash change
	$(window).hashchange(function(){self.onHashChange()});
	// dialog window Cancel button
	$('body').on('click', 'button.special_cancel', function(){
	    $(this).parents('div.window').data('kendoWindow').close()
	});
	// view choice buttons
	$('body').on('click', '#viewChoicePanel button', function(){
	    self.getContentByView($(this).attr('viewtype'), 
				  $(this).attr('viewid'));
	});
    }

    Djoe.prototype.pageOnLoad = function() {
	var self = this;
	this.ajaxErrorSetup();
	this.setGlobalEvents();
	$('.topbar-container > div > ul').kendoMenu();

	if ($(".sidebar").length) {
	    this.menuPanel = new Djoe.MenuPanel(this).init();
	    if (location.hash)
		$(window).hashchange();
	    else
		this.menuPanel.selectFirst();
	}
    };

    Djoe.prototype.setStateFromHash = function(hash) {
	hash = hash || location.hash;
	this.state = {};

	if (!hash)
	    return
	var splitedHash = hash.split('/'),
	part;
	for (var i = 0, l = splitedHash.length; i<l; i++){
	    part = splitedHash[i];
	    if (part == 'menu')
		this.state.menuId = parseInt(splitedHash[i+1])
	    if (part == 'view') {
		this.state.viewType = splitedHash[i+1];
		this.state.viewId = parseInt(splitedHash[i+2]);
	    }
	}
    };

    Djoe.prototype.onHashChange = function() {
	this.setStateFromHash();
	if ($('.window').length)
	    $('.window').data('kendoWindow').close();
	if (this.state.menuId !== this.menuId) {
	    this.menuId = this.state.menuId;
	    this.getContentByMenu();
	}
	else if (this.state.viewType !== this.view.type) {
	    console.log(this.view);
	    this.view.show(this.state.viewType)
	}
    };

    Djoe.prototype.getContentByMenu = function() {
	var self = this;
	return $.getJSON('./menu/' + this.menuId + '/', function(json){
	    self.menuPanel.reactivate();

	    if (json.target == 'new')
		return self.makeWindow(json.view_html, null, json.name)

	    if (json.target == 'current') {
		$('.content').html('');
		json.container = $('.content');
		self.view = new Djoe.View().init(self, json)
		self.view.show(self.state.viewType);
	    }
	});
    };


    Djoe.prototype.getContentByView = function() {
	var self = this;
	this.viewChoicePanelButtonState();
	$.getJSON('../../get_view/', this.currentView,
		  function(json){
		      $('.content').html(json.view_html)
		      self.fragmentInit($('.content'))
		  })
    };



    Djoe.prototype.makeWindow = function(content, url, title) {
	var self = this;
	this.windowCount++
	var window = $('<div class="window"/>');
	if (content)
	    window.html(content)
	$('body').append(window);

	var opts = {
            width: "80%",
            title: title,
	    modal: true,
	    refresh: function(){self.fragmentInit(this.wrapper, 'm2o')},
            close: function(){
		self.windowCount--;
		this.destroy();
	    },
        }
	if (url)
	    opts.content = url;
	window.kendoWindow(opts);
	window.data("kendoWindow").center().open();
	var wrapp = window.data("kendoWindow").wrapper;
	self.fragmentInit(wrapp);
	wrapp.css({
	    'left': parseInt(wrapp.css('left')) * (1 - .1*this.windowCount),
	    'top': parseInt(wrapp.css('top')) *  (1 - .1*this.windowCount),
	});
    }

    Djoe.prototype.m2oChange = function(id) {
	$parent = currentM2O[currentM2O.length-1].parents('.m2o_field');
	$parent.find('input:hidden').val(id);
	var url = $parent.attr('get_name');
	$.getJSON(url.replace('/0/', '/' + id + '/'), {}, function(data){
	    $parent.find('input.m2o_title').val(data.name);
	});
	$parent.find('a').show();
    };

    Djoe.prototype.gridChange = function(el, type) {
	if (type != 'm2o')
	    return;
	m2oChange(el.attr('rowId'));
	el.parents('.window').data('kendoWindow').close();
    };

    Djoe.prototype.fragmentInit = function(fragment, type) {
	fragment = fragment || $('body');
	fragment.find('span input:text').each(function(){
	    var $this  =$(this);
	    $this.hasClass('date_widget') ? 
		$this.kendoDatePicker({format:'yyyy-MM-dd'})
	    : $this.kendoAutoComplete({enable:false});
	});
	//fragment.find('span select').kendoDropDownList();

	fragment.find(".form_notebook li:first").addClass("k-state-active");
	fragment.find(".form_notebook").kendoTabStrip();
	fragment.find("input:file").kendoUpload();

	/*
	fragment.find('div.edit_form > form').submit(function(){
	    var submitForm = this;
	    $.post($(this).attr('action'), $(this).serialize(),
		   function(data) {
		       if (data.href) {
			   if (type == 'm2o') {
			       m2oChange(data.id);
			       fragment.parents('.window').data('kendoWindow').close();
			   } else {
			       window.location.href = data.href;
			   }
		       }
		       if (data.errors) {
			   fragment.find('.error-field').removeClass('.error_field');
			   alert_mess = '';
			   for (k in data.errors) {
			       alert_mess += data.errors[k];
			       $(submitForm[k]).addClass('.error_field');
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
	*/
	fragment.find(".tree-grid").each(function() {
	    $this = $(this);
	    if ($this.attr('static') ){
		opts = {}
	    } else {
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
	    };
	    $this.kendoGrid(opts);

	    var perPage = $('<select><option value="20">20</option><option value="50">50</option><option value="100">100</option></select>')
		.css({float:"right",
		      width:"100px"})
		.change(function(){
		    ds.options.pageSize = $(this).val();
		    ds._pageSize = $(this).val();
		    ds._take = $(this).val();
		    ds.read();
		    $this.data('kendoGrid').refresh();
		});
	    $this.next('.k-grid-pager').append(perPage);
	    perPage.kendoDropDownList();
	});
    }

    /*******************************************************************/
    /* Constructors
    /******************************************************************/

    // Menu panel
    Djoe.MenuPanel = function(djoe){
	this.djoe = djoe;
    };
    Djoe.MenuPanel.prototype.init = function(){
	var panel = $(".sidebar > ul").kendoPanelBar();
	panel.css({ width: 210 });
	this.panelBar = panel.data("kendoPanelBar");
	return this;
    };
    Djoe.MenuPanel.prototype.reactivate = function() {
	var curMenu = $('#panelmenu' + this.djoe.menuId);
	this.panelBar.expand(curMenu.parents('li'));
	this.panelBar.select(curMenu.parent());
    };
    Djoe.MenuPanel.prototype.selectFirst = function() {
	this.panelBar.expand($(".sidebar > ul > li:first"));
	this.panelBar.select($(".sidebar > ul > li:first"))
    };

    // VIEW
    Djoe.View = function(){};

    Djoe.View.prototype.VIEW_TYPES = ['tree', 'form', 'graph', 'calendar', 'gantt'];
    Djoe.View.prototype.VIEW_ICONS = {
	tree: 'k-search',
	form: 'k-edit',
	graph: 'k-insert',
	calendar: 'k-icon-calendar',
	gantt: ''
    }

    Djoe.View.prototype.init = function(djoe, options) {
	this.djoe = djoe;
	this.container = options.container;
	this.help = options.help;
	this.views = options.views;
	this.viewType = options.view_type;
	this.viewHtml = options.view_html;
	this.model = options.model;
	this.name = options.name;
	this.searchViewHtml = options.search_view_html;
	this.searchViewId = options.searchViewId;
	this.dataUrl = options.dataUrl;

	this.choicePanel = undefined;
	this.searchPanel = undefined;
	this.helpPanel = undefined;
	this.mainPanel = undefined;
	this.dataSource = undefined;

	this.makeChoicePanel();
	return this;
    };

    Djoe.View.prototype._viewLink = function(viewType, suff) {
	var link = '#!/'; 
	link += ['menu', this.djoe.menuId, 'view', viewType, 
		 this.views[viewType]].join('/');
	if (suff)
	    link += suff;
	return link;
    };

    Djoe.View.prototype.makeChoicePanel = function() {
	if ($('#viewChoicePanel').length)
	    return
	var panel = $('<div id="viewChoicePanel"/>'),
	icon, but, viewType, i, l;
	for (i = 0, l = this.VIEW_TYPES.length; i < l; i++) {
	    viewType = this.VIEW_TYPES[i];
	    if (typeof this.views[viewType] == 'undefined')
		continue
	    icon = $('<span class="k-icon"/>');
	    icon.addClass(this.VIEW_ICONS[viewType]);
	    but = $('<a class="k-button"/>');
	    but.addClass('but_view_' + viewType);
	    but.attr('href', this._viewLink(viewType));
	    but.append(icon);
	    panel.append(but);
	}
	this.choicePanel = panel;
	this.container.prepend(panel);
    };

    Djoe.View.prototype.choicePanelState = function(){
	$('#viewChoicePanel a').removeClass('k-state-selected');
	$('#viewChoicePanel a.but-view-' + this.viewType).addClass('k-state-selected');
    }

    Djoe.View.prototype.getHelpPanel = function() {
	if (!this.helpPanel) {
	    this.helpPanel = $('<div id="viewHelpPanel">' 
			       + (this.help || '') 
			       + '</div>');
	    this.container.append(this.helpPanel);
	}
	return this.helpPanel
    };

    Djoe.View.prototype.getMainPanel = function() {
	if (!this.mainPanel) {
	    this.mainPanel = $('<div id="viewMainPanel"/>');
	    this.container.append(this.mainPanel);
	}
	return this.mainPanel
    };

    
    Djoe.View.prototype.getDataSource = function() {
	if (!this.dataSource) {
	    this.dataSource = new kendo.data.DataSource({
		transport: {
		    read: { 
			url: this.dataUrl,
			dataType: "json"
		    }
		},
		schema: {data:'data', total:'total'},
		pageSize: 20,
		serverPaging: true,
		serverSorting: true
	    });
	}
	return this.dataSource
    };

    Djoe.View.prototype.show = function(viewType) {
	this.viewType = viewType || this.viewType;
	this.choicePanelState();
	this.getHelpPanel().show();
	return this['show_' + this.viewType]()
    };

    Djoe.View.prototype.show_tree = function() {
	var self = this;
	this.show_search();
	this.getMainPanel().html(this.viewHtml);
	var element = this.mainPanel.find('table');
	opts = {
	    dataSource: this.getDataSource(),
	    scrollable: false,
	    sortable: {
		mode: 'multiple',
		allowUnsort: true
	    },
	    selectable: 'multiple row',
	    navigatable: true,
	    pageable: true,
	    change: function(){gridChange(this.select(), type)},
	    rowTemplate: kendo.template(element.prev().html())
	};
	element.kendoGrid(opts);
	this.getMainPanel().find('.grid-panel a.new-button')
	    .attr('href', this._viewLink('form'));
	var perPage = $('<select/>'), opt, val;
	for (var i = 0, l = this.djoe.PER_PAGES.length; i<l; i++) {
	    val = this.djoe.PER_PAGES[i];
	    opt = $('<option/>')
		.text(val)
		.val(val);
	    perPage.append(opt)
	}
	perPage.css({float:"right",
		     width:"100px"})
	    .change(function(){
		self.dataSource.pageSize(parseInt($(this).val()));
	    });
	element.next('.k-grid-pager').append(perPage);
	perPage.kendoDropDownList();
    };

    Djoe.View.prototype.show_search = function() {
	if (!this.searchPanel) {
	    this.searchPanel = $('<div id="viewSearchPanel"/>');
	    this.searchPanel.html(this.searchViewHtml);
	    this.container.append(this.searchPanel);
	    this.djoe.fragmentInit(this.searchPanel);
	}
	return this.searchPanel.show()
    };

    Djoe.View.prototype.show_form = function() {
	var self = this;
	this.getViewHtml('form', function(json){
	    if (self.searchPanel)
		self.searchPanel.hide();
	    self.getHelpPanel().hide();
	    var panel = self.getMainPanel().html(json.view_html);
	    panel.find('form').submit(self.editFormSubmit);
	    self.djoe.fragmentInit(panel);
	});
    };

    Djoe.View.prototype.editFormSubmit = function() {
	var $form = $(this);
	$.post($form.attr('action'), $form.serialize(), function(json) {
	    if (json.errors) {
		html = []
		for (err in json.errors)
		    html.push(json.errors[err])
		$('#errorDialog').html(html.join('')).data('kendoWindow').title('Validation Errors')
		.center()
		.open();
	    }
	    console.log(json);
	}, 'json');
	return false;
    };

    Djoe.View.prototype.show_graph = function() {

    };

    Djoe.View.prototype.show_calendar = function() {

    };


    Djoe.View.prototype.getViewHtml = function(type, callback) {
	var self = this;
	var data = {type:type, model:this.model, id:this.views[type]}
	$.getJSON('../../get_view/', data, callback)
    };
/*


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
	    refresh: function(){fragmentInit(this.wrapper, 'm2o')},
	    
            close: function(){windowCount--; currentM2O.pop()}
        });
	window.data("kendoWindow").center();
	var wrapp = window.data("kendoWindow").wrapper;
	wrapp.css({'left': parseInt(wrapp.css('left')) * (1-.1*windowCount),
		   'top': parseInt(wrapp.css('top')) *  (1-.1*windowCount),
		  });
	return false;
    });

    fragmentInit();
*/
var djoe = new Djoe();
djoe.pageOnLoad();

});