$(document).ready(function() {
    //$('#main').on('submit','#comment_form', function() {
        //event.preventDefault();
        //var $form = $( this ),
            //url=$form.attr("action"),
            //data=$form.serialize();
        //var r = $.post(url, data);
        //r.done(function(data) {
            //if (data.hasOwnProperty('success')) {
                //line = "<li class='list-group-item'>@"+data.username+" ("+data.time+"): "+data.comment;
                //$( "#comments" ).append(line);
            //} else {
              //line='<div class="alert alert-dismissable alert-danger"><button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button><strong>'+data.error+'</strong></div>';
                //$( '#messages').append(line);}
            //});
        //$('#comment').val('');
    //});
    $(document).on('submit','form:not(#loginForm)', function(event) {
        event.preventDefault();
        var $form = $( this ),
            url=$form.attr("action"),
            body=$form.serialize();
        var request = $.ajax({
            type: "POST",
            url: url,
            data: body})
        request.done(function(data) {
                if (data.redirect) {
                    //history.pushState({id: data.redirect}, '', data.redirect);
                    loadPage(data.redirect);
                } else {
                    history.pushState({id: url}, '', url);
                    d = $(data.page).filter('#main').children();
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
                d = $(data.page).filter('#main').contents();
                $main.empty().append(d);
            } else {
                history.pushState({id: href}, '', href);
                d = $(data).filter('#main').contents();
                $main.empty().append(d);
            }})
            //$main.load(href + " #main>*", ajaxLoad);
      };

      //Back button to work
      $(window).on("popstate", function(e) {
        if (e.originalEvent.state !== null) {
        $.get(location.href, function(data) {
            if (data.page) {
                d = $(data.page).filter('#main').contents();
                $main.empty().append(d);
            } else {
                d = $(data).filter('#main').contents();
                $main.empty().append(d);
            }})
          //loadPage(location.href);
        }
      });

      //Select all links except the dropdown buttons, logout button, service
      //fee
      $(document).on("click", "a:not(.dropdown-toggle):not(#logout):not(#serviceFee), area, .clickableRow", function(event) {
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
