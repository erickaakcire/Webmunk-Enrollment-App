$.expr.pseudos.webmunkRandomMirror = $.expr.createPseudo(function (parameters) {
  const paramTokens = parameters.split(' ')

  const toMatch = $(paramTokens[0])
  let tagged = $(paramTokens[1] + '[data-webmunk-mirror="' + paramTokens[0] + '"]')
  let toTag = $(paramTokens[1] + ':not([data-webmunk-mirror="' + paramTokens[0] + '"])')

  while (toMatch.length > tagged.length && toTag.length > 0) {
    const randomIndex = Math.floor(Math.random() * toTag.length)

    $(toTag.get(randomIndex)).attr('data-webmunk-mirror', paramTokens[0])

    tagged = $(paramTokens[1] + '[data-webmunk-mirror="' + paramTokens[0] + '"]')
    toTag = $(paramTokens[1] + ':not([data-webmunk-mirror="' + paramTokens[0] + '"])')
  }

  return function (elem) {
    const attrValue = $(elem).attr('data-webmunk-mirror')

    if (attrValue !== undefined) {
      return attrValue === paramTokens[0]
    }

    return false
  }
})

$.expr.pseudos.webmunkContainsInsensitive = $.expr.createPseudo(function (query) {
  return function (elem) {
    return $(elem).text().toUpperCase().indexOf(query.toUpperCase()) >= 0
  }
})

$.expr.pseudos.isAmazonProductItem = $.expr.createPseudo(function (parameters) {
  const addSelectors = [
    '[data-asin!=""][data-asin]', // Element has ASIN
    // '[data-csa-c-asin!=""][data-csa-c-asin]', // Element has ASIN
    '.a-carousel-card:has([href*="/dp/"])', // Sponsored links w ASIN in URL: "/dp/ASIN/"
    '.a-carousel-card:has([href*="/gp/slredirect"])', // Sponsored links w/o ASIN
    '.a-section:has(.sbv-product-container)', // Product w/ video ad
    'th.comparison_image_title_cell', // Comparison table
    'td.comparison_add_to_cart_button', // Comparison table
    '#ape_Detail_dp-ads-center-promo_Desktop_placement', // Large page ad
    'div#ad:has([href*="/dp/"])', // 
    'div#ad:has(picture[data-testid="productImage"])', // 
  ]

  const clearSelectors = [
    '#reviews-image-gallery-container', // Review images
    '[data-video-url]' // Product videos,
  ]

  addSelectors.forEach(function(selector) {
    $(parameters + selector).attr('data-webmunk-is-amazon-item', 'true')
  })

  clearSelectors.forEach(function(selector) {
    $(selector).removeAttr('data-webmunk-is-amazon-item')
  })

  const items = $('[data-webmunk-is-amazon-item]')

  return function (elem) {
	const attrValue = $(elem).attr('data-webmunk-is-amazon-item')

	if (attrValue === 'true') {
	  return true
	}

	return false
  }
})

// jQuery.expr[':'].icontains = function(a, i, m) {
//  return jQuery(a).text().toUpperCase()
//      .indexOf(m[3].toUpperCase()) >= 0;
// };

let counts = {}

window.webmunkRuleMatches.forEach(function (match) {
  const matches = $(document).find(match)

  counts[match] = matches.length
})

console.log('WEBMUNK-JSON:' + window.btoa(JSON.stringify(counts)))
