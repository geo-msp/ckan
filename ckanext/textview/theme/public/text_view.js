ckan.module('text_view', function (jQuery, _) {
  return {
    options: {
      i18n: {
        error: '<p style="font-family: \'Dosis\', sans-serif;font-size:16px;">Les données ne peuvent être visualisées.<br>Elles sont disponibles pour le téléchargement par le bouton Télécharger ci-haut. <br>Pour tout problème avec ce jeu de données, veuillez  <a href="/fr/contact">communiquez avec nous</a></p>'
      },
      parameters: {
        json: {
          contentType: 'application/json',
          dataType: 'json',
          dataConverter: function (data) { return JSON.stringify(data, null, 2); },
          language: 'json'
        },
        jsonp: {
          contentType: 'application/javascript',
          dataType: 'jsonp',
          dataConverter: function (data) { return JSON.stringify(data, null, 2); },
          language: 'json'
        },
        xml: {
          contentType: 'text/xml',
          dataType: 'text',
          language: 'xml'
        },
        text: {
          contentType: 'text/plain',
          dataType: 'text',
          language: ''
        }
      }
    },
    initialize: function () {
      var self = this;
      var format = preload_resource['format'].toLowerCase();

      var TEXT_FORMATS = preview_metadata['text_formats'];
      var XML_FORMATS = preview_metadata['xml_formats'];
      var JSON_FORMATS = preview_metadata['json_formats'];
      var JSONP_FORMATS = preview_metadata['jsonp_formats'];

      var p;

      if (JSON_FORMATS.indexOf(format) !== -1) {
        p = this.options.parameters.json;
      } else if (JSONP_FORMATS.indexOf(format) !== -1) {
        p = this.options.parameters.jsonp;
      } else if(XML_FORMATS.indexOf(format) !== -1) {
        p = this.options.parameters.xml;
      } else {
        p = this.options.parameters.text;
      }

      jQuery.ajax(resource_url, {
        type: 'GET',
        contentType: p.contentType,
        dataType: p.dataType,
        success: function(data, textStatus, jqXHR) {
          data = p.dataConverter ? p.dataConverter(data) : data;
          var highlighted;

          if (p.language) {
            highlighted = hljs.highlight(p.language, data, true).value;
          } else {
            highlighted = '<pre>' + data + '</pre>';
          }

          self.el.html(highlighted);
        },
        error: function(jqXHR, textStatus, errorThrown) {
          if (textStatus == 'error' && jqXHR.responseText.length) {
            self.el.html('<p style="font-family: \'Dosis\', sans-serif;font-size:16px;">Les données ne peuvent être visualisées.<br>Elles sont disponibles pour le téléchargement par le bouton Télécharger ci-haut. <br>Pour tout problème avec ce jeu de données, veuillez  <a href="/fr/contact">communiquez avec nous</a></p>');
          } else {
            self.el.html(self.i18n('error', {text: textStatus, error: errorThrown}));
          }
        }
      });
    }
  };
});
