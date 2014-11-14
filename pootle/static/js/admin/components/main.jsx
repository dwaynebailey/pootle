'use strict';

var React = require('react');
var _ = require('underscore');
var Backbone = require('backbone');

var Search = require('./search');
var User = require('./user');


var AdminApp = React.createClass({

  /* Lifecycle */

  getInitialState: function () {
    return {
      items: new this.props.collection(),
      selectedItem: null,
      searchQuery: '',
      view: 'edit'
    };
  },

  setupRoutes: function (router) {

    router.on('route:main', function (qs) {
      var searchQuery = '';
      qs !== undefined && (searchQuery = qs.q);
      this.handleSearch(searchQuery);
    }.bind(this));

    router.on('route:edit', function (id, qs) {
      var item = new this.props.model({id: id});
      this.handleSelectItem(item);
    }.bind(this));
  },

  componentWillMount: function () {
    this.setupRoutes(this.props.router);
    Backbone.history.start({pushState: true, root: this.props.appRoot});
  },

  componentWillUpdate: function (nextProps, nextState) {
    this.handleURL(nextState);
  },


  /* State-changing handlers */

  handleSearch: function (query, extraState) {
    var newState = extraState || {};

    if (query !== this.state.searchQuery) {
      newState.searchQuery = query;
      newState.selectedItem = null;
    }

    return this.state.items.search(query).then(function () {
      newState.items = this.state.items;
      this.setState(newState);
    }.bind(this));
  },

  handleSelectItem: function (item) {
    var newState = {selectedItem: item, view: 'edit'};

    if (this.state.items.contains(item)) {
      this.setState(newState);
    } else {
      item.fetch().then(function () {
        this.handleSearch(this.state.searchQuery, newState);
      }.bind(this));
    }
  },

  handleAdd: function () {
    this.setState({selectedItem: null, view: 'add'});
  },

  handleCancel: function () {
    this.setState({selectedItem: null, view: 'edit'});
  },

  handleSave: function (item) {
    this.handleSelectItem(item);
    PTL.msg.show({
      text: gettext('Saved successfully.'),
      level: 'success'
    });
  },

  handleDelete: function () {
    this.setState({selectedItem: null});
    PTL.msg.show({
      text: gettext('Deleted successfully.'),
      level: 'danger'
    });
  },


  /* Handlers */

  handleURL: function (newState) {
    var router = this.props.router,
        query = newState.searchQuery,
        newURL;

    if (newState.selectedItem) {
      newURL = ['edit', newState.selectedItem.get('id'), ''].join('/');
    } else {
      var params = query === '' ? {} : {q: query};
      newURL = router.toFragment('', params);
    }

    router.navigate(newURL);
  },


  /* Layout */

  render: function () {
    var viewsMap = {
      add: <User.UserAdd
              model={this.props.model}
              collection={this.state.items}
              handleSuccess={this.handleSave}
              handleCancel={this.handleCancel} />,
      edit: <User.UserEdit
              model={this.state.selectedItem}
              collection={this.state.items}
              handleAdd={this.handleAdd}
              handleSuccess={this.handleSave}
              handleDelete={this.handleDelete} />
    };

    return (
      <div>
        <div className="module first">
          <Search
            handleSearch={this.handleSearch}
            handleSelectItem={this.handleSelectItem}
            items={this.state.items}
            selectedItem={this.state.selectedItem}
            searchQuery={this.state.searchQuery} />
        </div>

        <div className="module admin-content">
          {viewsMap[this.state.view]}
        </div>
      </div>
    );
  }
});


module.exports = AdminApp;
