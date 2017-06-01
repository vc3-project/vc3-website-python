jQuery(document).ready(function() {
  "use strict";

  var pluginName = "Morphext",
  defaults = {
    animation: "bounceIn",
    separator: ",",
    speed: 2000,
    complete: jQuery.noop
  };

  function Plugin (element, options) {
    this.element = jQuery(element);
    this.settings = jQuery.extend({}, defaults, options);
    this._defaults = defaults;
    this._init();
  }

  Plugin.prototype = {
    _init: function () {
      var jQuerythat = this;
      this.phrases = [];

      this.element.addClass("morphext");

      jQuery.each(this.element.text().split(this.settings.separator), function (key, value) {
        jQuerythat.phrases.push(jQuery.trim(value));
      });

      this.index = -1;
      this.animate();
      this.start();
    },
    animate: function () {
      this.index = ++this.index % this.phrases.length;
      this.element[0].innerHTML = "<span class=\"animated " + this.settings.animation + "\">" + this.phrases[this.index] + "</span>";

      if (jQuery.isFunction(this.settings.complete)) {
        this.settings.complete.call(this);
      }
    },
    start: function () {
      var jQuerythat = this;
      this._interval = setInterval(function () {
        jQuerythat.animate();
      }, this.settings.speed);
    },
    stop: function () {
      this._interval = clearInterval(this._interval);
    }
  };

    jQuery.fn[pluginName] = function (options) {
      return this.each(function() {
        if (!jQuery.data(this, "plugin_" + pluginName)) {
          jQuery.data(this, "plugin_" + pluginName, new Plugin(this, options));
        }
      });
    };

  // Preloader
  jQuery(window).load(function(){
    jQuery('#preloader').delay(100).fadeOut('slow',function(){jQuery(this).remove();});
  });

  // Hero rotating texts
  jQuery("#hero .rotating").Morphext({
    animation: "flipInX",
    separator: ",",
    speed: 3000
  });

  // Initiate the wowjs
  new WOW().init();

  // Initiate superfish on nav menu
  jQuery('.nav-menu').superfish({
    animation: {opacity:'show'},
    speed: 400
  });

  // Mobile Navigation
  if( jQuery('#nav-menu-container').length ) {
      var jQuerymobile_nav = jQuery('#nav-menu-container').clone().prop({ id: 'mobile-nav'});
      jQuerymobile_nav.find('> ul').attr({ 'class' : '', 'id' : '' });
      jQuery('body').append( jQuerymobile_nav );
      jQuery('body').prepend( '<button type="button" id="mobile-nav-toggle"><i class="fa fa-bars"></i></button>' );
      jQuery('body').append( '<div id="mobile-body-overly"></div>' );
      jQuery('#mobile-nav').find('.menu-has-children').prepend('<i class="fa fa-chevron-down"></i>');

      jQuery(document).on('click', '.menu-has-children i', function(e){
          jQuery(this).next().toggleClass('menu-item-active');
          jQuery(this).nextAll('ul').eq(0).slideToggle();
          jQuery(this).toggleClass("fa-chevron-up fa-chevron-down");
      });

      jQuery(document).on('click', '#mobile-nav-toggle', function(e){
          jQuery('body').toggleClass('mobile-nav-active');
          jQuery('#mobile-nav-toggle i').toggleClass('fa-times fa-bars');
          jQuery('#mobile-body-overly').toggle();
      });

      jQuery(document).click(function (e) {
          var container = jQuery("#mobile-nav, #mobile-nav-toggle");
          if (!container.is(e.target) && container.has(e.target).length === 0) {
             if ( jQuery('body').hasClass('mobile-nav-active') ) {
                  jQuery('body').removeClass('mobile-nav-active');
                  jQuery('#mobile-nav-toggle i').toggleClass('fa-times fa-bars');
                  jQuery('#mobile-body-overly').fadeOut();
              }
          }
      });
  } else if ( jQuery("#mobile-nav, #mobile-nav-toggle").length ) {
      jQuery("#mobile-nav, #mobile-nav-toggle").hide();
  }

  // Stick the header at top on scroll
  jQuery("#header").sticky({topSpacing:0, zIndex: '50'});

  // Smoth scroll on page hash links
  jQuery('a[href*="#"]:not([href="#"])').on('click', function() {
      if (location.pathname.replace(/^\//,'') == this.pathname.replace(/^\//,'') && location.hostname == this.hostname) {
          var target = jQuery(this.hash);
          if (target.length) {

              var top_space = 0;

              if( jQuery('#header').length ) {
                top_space = jQuery('#header').outerHeight();
              }

              jQuery('html, body').animate({
                  scrollTop: target.offset().top - top_space
              }, 1500, 'easeInOutExpo');

              if ( jQuery(this).parents('.nav-menu').length ) {
                jQuery('.nav-menu .menu-active').removeClass('menu-active');
                jQuery(this).closest('li').addClass('menu-active');
              }

              if ( jQuery('body').hasClass('mobile-nav-active') ) {
                  jQuery('body').removeClass('mobile-nav-active');
                  jQuery('#mobile-nav-toggle i').toggleClass('fa-times fa-bars');
                  jQuery('#mobile-body-overly').fadeOut();
              }

              return false;
          }
      }
  });

  // Back to top button
  jQuery(window).scroll(function() {

      if (jQuery(this).scrollTop() > 100) {
          jQuery('.back-to-top').fadeIn('slow');
      } else {
          jQuery('.back-to-top').fadeOut('slow');
      }

  });

  jQuery('.back-to-top').click(function(){
      jQuery('html, body').animate({scrollTop : 0},1500, 'easeInOutExpo');
      return false;
  });

  // Modal
  jQuery('#myModal').on('shown.bs.modal', function () {
    jQuery('#myInput').focus()
  });
});

// Tab Panels
jQuery(document).on('show.bs.tab', '.nav-tabs-responsive [data-toggle="tab"]', function(e) {
  var jQuerytarget = jQuery(e.target);
  var jQuerytabs = jQuerytarget.closest('.nav-tabs-responsive');
  var jQuerycurrent = jQuerytarget.closest('li');
  var jQueryparent = jQuerycurrent.closest('li.dropdown');
  jQuerycurrent = jQueryparent.length > 0 ? jQueryparent : jQuerycurrent;
  var jQuerynext = jQuerycurrent.next();
  var jQueryprev = jQuerycurrent.prev();
  var updateDropdownMenu = function(jQueryel, position){
    jQueryel
      .find('.dropdown-menu')
      .removeClass('pull-xs-left pull-xs-center pull-xs-right')
      .addClass( 'pull-xs-' + position );
  };

  jQuerytabs.find('>li').removeClass('next prev');
  jQueryprev.addClass('prev');
  jQuerynext.addClass('next');

  updateDropdownMenu( jQueryprev, 'left' );
  updateDropdownMenu( jQuerycurrent, 'center' );
  updateDropdownMenu( jQuerynext, 'right' );
});
