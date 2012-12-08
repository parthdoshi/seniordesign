jQuery(function($) {

	$('#navigation .sub-menu').wrap('<div class="dd" />');
	
	$('#navigation ul li').hover(function(){
			$("a:eq(0)", this).addClass("hover");
			$(this).find('.dd:eq(0)').show();
		}, function(){
			$("a:eq(0)", this).removeClass("hover");
			$(this).find('.dd:eq(0)').hide();
		}
	);
	
	$('#slider ul').jcarousel({
		wrap: 'circular',
		scroll: 1,
		auto: 10,
		visible: 1,
		initCallback: init_carousel,
		animation: '100'
	});
	
	$('.gallery-slider ul').jcarousel({
		wrap: 'both',
		scroll: 1,
		auto: 0,
		visible: 7,
		initCallback: init_carousel_two
	});
	
	$('.thumb-image').click(function(){
		var image = $(this).attr('href');
		$("#big-image").attr('src', image);
		return false;
	});

	
	if ($.browser.msie && $.browser.version.substr(0,1)<7) {
		DD_belatedPNG.fix('#slider ul li .cnt, #slider .nav a.prev, #slider .nav a.next, .featured-boxes .box a.cnt span.strike-bg');
	};
	
	/* Center the Nav */
	
	var padd = 28;
	var elements = $('#navigation ul:first').children().size();
	var ul_width = $('#navigation ul').outerWidth();
	var nav_width = $('#navigation').outerWidth();	
	
	padd = (nav_width - ul_width)/2;
	$('#navigation ul:eq(0)').css({'padding-left': padd});

	function init_carousel(carousel) {
		$('#slider .nav a.prev').click(function(){
			carousel.prev();
			return false;
		});
		$('#slider .nav a.next').click(function(){
			carousel.next();
			return false;
		});
	}

	function init_carousel_two(carousel) {
		$('.gallery-slider .nav a.prev').click(function(){
			carousel.prev();
			return false;
		});
		$('.gallery-slider .nav a.next').click(function(){
			carousel.next();
			return false;
		});
	}
	$('#footer .nav li').not(':last').each(function() {
		$(this).append('<span> | </span>');
	});

});