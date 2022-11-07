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
