/*
 * Root javascript file
 */

/// Define namespace(s)
var rentport = rentport || {}

/// Check for multiple inclusions
var isFirstLoad = function (ns, file) {
    var isFirst = ns.firstload === undefined;
    ns.firstload = false;
    if (!isFirst) {
        console.log('included again:' + file);
    }
    return isFirst
};

$(document).ready(function() {

        // Prevent re-import
        if (!isFirstLoad(rentport, 'rentport.js')) {
            return;
        }

        // Options for pwstrength plugin
        "use strict";
        var options = {};
        options.ui = {
            scores: Array(30, 40, 55, 70),
            container: "#pwd-container",
            showVerdictsInsideProgressBar: true,
            viewports: {
                progress: ".pwstrength_viewport_progress"
            }
        };
        options.common = {
            zxcvbn: true,
            // Default disabled
            onLoad: function () {
                if ($('#password').val() == null)
                    $('#submit').prop('disabled', true);
                else if (zxcvbn($('#password').val()).score >= 4)
                    $('#submit').prop('disabled', false);
                else
                    $('#submit').prop('disabled', true);
           },

            // Disable submit for bad passwords
            // Enable for good enough passwords
            onKeyUp: function () {
                if (zxcvbn($('#password').val()).score >= 4)
                    $('#submit').prop('disabled', false);
                else
                    $('#submit').prop('disabled', true);
                   }
        };

    // Password strength bar
    $(document).on('focus', ':password', function() {
        $(this).pwstrength(options);
    });

    // Autocomplete user search
    $(document).on('focus', '#userSearch', function() {
        $(this).marcoPolo({
          url: '/user/search',
          required: 'true',
          formatData: function(data) {
            return data.results;
          },
          formatItem: function (data, $item) {
            return data.username;
          },
          onSelect: function (data, $item) {
            this.val(data.username);
          }
        });
    });
    $(document).on('submit','form:not(#loginForm):not(#registerForm)', function(event) {
        event.preventDefault();
        var $form = $( this ),
            url=$form.attr("action"),
            body= new FormData(this);
        var request = $.ajax({
            type: "POST",
            url: url,
            data: body,
            mimeType: "multipart/form-data",
            dataType: "json",
            contentType: false,
                cache: false,
                processData: false})
        request.done(function(data) {
                if (data.redirect) {
                    //history.pushState({id: data.redirect}, '', data.redirect);
                    loadPage(data.redirect);
                } else {
                    history.pushState({id: url}, '', url);
                    var d = $(data.page).filter('#main').children();
                    $( "#main" ).empty().append( d );
                }
            })});

      String.prototype.decodeHTML = function() {
        return $("<div>", {html: "" + this}).html();
      };
      var $main = $("#main"),
      ajaxLoad = function(html) {
        document.title = html
          .match(/<title>(.*?)<\/title>/)[1]
          .trim()
          .decodeHTML();
      },
      loadPage = function(href) {
        $.get(href, function(data) {
            if (data.redirect) {
                //history.pushState({id: data.redirect}, '', data.redirect);
                loadPage(data.redirect);
            } else if (data.page) {
                history.pushState({id: href}, '', href);
                var d = $(data.page).filter('#main').contents();
                $main.empty().append(d);
            } else {
                history.pushState({id: href}, '', href);
                var d = $(data).filter('#main').contents();
                $main.empty().append(d);
            }})
            //$main.load(href + " #main>*", ajaxLoad);
      };

      //Back button to work
      $(window).on("popstate", function(e) {
        if (e.originalEvent.state !== null) {
        $.get(location.href, function(data) {
            if (data.page) {
                var d = $(data.page).filter('#main').contents();
                $main.empty().append(d);
            } else {
                var d = $(data).filter('#main').contents();
                $main.empty().append(d);
            }})
          //loadPage(location.href);
        }
      });

      // To make rows, tables, etc. linkable to outside URLs
      $(document).on("click", ".outsideURL", function(event) {
          var href = $(this).attr("href");
          if (href) {
                window.location = href;
          }
        });

      //Select all links except the dropdown buttons, logout button, service
      //fee, etc
      $(document).on("click", "a:not(.dropdown-toggle):not(.exempt), area, .clickableRow", function(event) {
        event.preventDefault();
        var href = $(this).attr("href");

        if (href.indexOf(document.domain) > -1
          || href.indexOf(':') === -1)
        {
          loadPage(href);
          // Since ajax, initiate dropdown toggle (to hide)
          $('.dropdown.open .dropdown-toggle').dropdown('toggle');
          // Remove old active class
          //$(this).parent('li').siblings( ".active" ).removeClass('active');
          $('li .active').removeClass('active');
          // Add new active class
          $(this).parent('li').addClass('active');
        }
      });
});
