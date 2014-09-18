jQuery(document).ready(function($) {

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
        $main.load(href + " #main>*", ajaxLoad);
      };

      //Back button to work
      $(window).on("popstate", function(e) {
        if (e.originalEvent.state !== null) {
          loadPage(location.href);
        }
      });

      //Select all links except the dropdown buttons, logout button, service
      //fee
      $(document).on("click", "a:not(.dropdown-toggle):not(#logout):not(#serviceFee), area, .clickableRow", function() {
        var href = $(this).attr("href");

        if (href.indexOf(document.domain) > -1
          || href.indexOf(':') === -1)
        {
          history.pushState({id: href}, '', href);
          loadPage(href);
          // Since ajax, initiate dropdown toggle (to hide)
          $('.dropdown.open .dropdown-toggle').dropdown('toggle');
          // Remove old active class
          //$(this).parent('li').siblings( ".active" ).removeClass('active');
          $('li .active').removeClass('active');
          // Add new active class
          $(this).parent('li').addClass('active');
          return false;
        }
      });
});
