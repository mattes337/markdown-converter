/**
 * Shared utilities for markdown converter Apify actors
 * Ported from Python server.py and browser_utils.py
 */

const { chromium } = require('playwright');
const cheerio = require('cheerio');
const axios = require('axios');
const { URL } = require('url');

/**
 * Check if content is HTML by looking for HTML tags
 * @param {string|Buffer} content - Content to check
 * @returns {boolean} - True if content appears to be HTML
 */
function isHtmlContent(content) {
    const contentStr = typeof content === 'string' ? content : content.toString('utf-8');
    const htmlTags = ['<html', '<body', '<div', '<p', '<span', '<!doctype'];
    return htmlTags.some(tag => contentStr.toLowerCase().includes(tag));
}

/**
 * Extract content from <article> tag if present, otherwise return original content
 * @param {string} htmlContent - HTML content to process
 * @returns {string} - Extracted article content or original content
 */
function extractArticleContent(htmlContent) {
    const $ = cheerio.load(htmlContent);
    const article = $('article');
    
    if (article.length > 0) {
        return article.html();
    }
    
    return htmlContent;
}

/**
 * Clean HTML content by removing unwanted tags and attributes
 * @param {string} htmlContent - HTML content to clean
 * @param {string[]} unwantedTags - Array of tag names to remove
 * @param {string[]} unwantedAttrs - Array of attribute names to remove
 * @returns {string} - Cleaned HTML content
 */
function cleanHtml(htmlContent, unwantedTags = null, unwantedAttrs = null) {
    const $ = cheerio.load(htmlContent);
    
    // Default unwanted tags if not provided
    if (!unwantedTags) {
        unwantedTags = ['head', 'img', 'script', 'style', 'meta', 'link', 'noscript', 'iframe', 'embed', 'object'];
    }
    
    // Default unwanted attributes if not provided
    if (!unwantedAttrs) {
        unwantedAttrs = ['style', 'class', 'id', 'onclick', 'onload', 'onerror', 'data-.*', 'width', 'height', 'valign', 'role', 'align', 'cellspacing', 'border', 'cellpadding', 'aria-.*'];
    }
    
    // Remove unwanted tags completely
    unwantedTags.forEach(tagPattern => {
        if (tagPattern.includes('*') || tagPattern.includes('(')) {
            // Regex pattern - find all elements and check names
            const regex = new RegExp(tagPattern.replace('*', '.*'));
            $('*').each((i, elem) => {
                if (elem.name && regex.test(elem.name)) {
                    $(elem).remove();
                }
            });
        } else {
            // Exact match
            $(tagPattern).remove();
        }
    });
    
    // Remove unwanted attributes from all tags
    $('*').each((i, elem) => {
        const $elem = $(elem);
        const attrs = Object.keys(elem.attribs || {});
        
        attrs.forEach(attr => {
            let shouldRemove = false;
            
            unwantedAttrs.forEach(attrPattern => {
                if (attrPattern.includes('*') || attrPattern.includes('(')) {
                    // Regex pattern
                    const regex = new RegExp(attrPattern.replace('*', '.*'));
                    if (regex.test(attr)) {
                        shouldRemove = true;
                    }
                } else {
                    // Exact match
                    if (attr === attrPattern) {
                        shouldRemove = true;
                    }
                }
            });
            
            if (shouldRemove) {
                $elem.removeAttr(attr);
            }
        });
    });
    
    // Remove empty tags (except self-closing ones)
    $('*').each((i, elem) => {
        const $elem = $(elem);
        const selfClosingTags = ['br', 'hr', 'img', 'input', 'meta', 'link'];
        
        if (!selfClosingTags.includes(elem.name) && 
            $elem.text().trim() === '' && 
            $elem.children().length === 0) {
            $elem.remove();
        }
    });
    
    return $.html();
}

/**
 * Fetch content with browser fallback for handling bot detection
 * @param {string} url - URL to fetch
 * @param {number} timeout - Request timeout in seconds
 * @returns {Promise<{content: string, finalUrl: string, usedBrowser: boolean, contentType: string}>}
 */
async function fetchWithBrowserFallback(url, timeout = 30) {
    const headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    };
    
    try {
        // First try with regular HTTP request
        const response = await axios.get(url, {
            headers,
            timeout: timeout * 1000,
            maxRedirects: 10
        });
        
        return {
            content: response.data,
            finalUrl: response.request.res.responseUrl || url,
            usedBrowser: false,
            contentType: response.headers['content-type'] || ''
        };
    } catch (error) {
        // If regular request fails, try with browser
        console.log(`Regular request failed for ${url}, trying with browser: ${error.message}`);
        
        const browser = await chromium.launch({ headless: true });
        const context = await browser.newContext({
            userAgent: headers['User-Agent']
        });
        const page = await context.newPage();
        
        try {
            await page.goto(url, { waitUntil: 'networkidle', timeout: timeout * 1000 });
            const content = await page.content();
            const finalUrl = page.url();
            
            await browser.close();
            
            return {
                content,
                finalUrl,
                usedBrowser: true,
                contentType: 'text/html'
            };
        } catch (browserError) {
            await browser.close();
            throw new Error(`Both regular request and browser failed: ${error.message}, ${browserError.message}`);
        }
    }
}

/**
 * Dereference a URL by following redirects and return the final URL
 * @param {string} url - URL to dereference
 * @param {number} maxRedirects - Maximum number of redirects to follow
 * @returns {Promise<{originalUrl: string, finalUrl: string, redirectCount: number, redirectChain: string[], maxRedirectsReached: boolean}>}
 */
async function dereferenceUrl(url, maxRedirects = 20) {
    let redirectCount = 0;
    let currentUrl = url;
    const redirectChain = [url];
    
    const headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive'
    };
    
    while (redirectCount < maxRedirects) {
        try {
            const response = await axios.get(currentUrl, {
                headers,
                maxRedirects: 0,
                validateStatus: (status) => status < 400,
                timeout: 15000
            });
            
            // Check for redirect status codes
            if ([301, 302, 303, 307, 308].includes(response.status)) {
                const location = response.headers.location;
                if (location) {
                    // Handle relative URLs
                    if (location.startsWith('/')) {
                        const urlObj = new URL(currentUrl);
                        currentUrl = `${urlObj.protocol}//${urlObj.host}${location}`;
                    } else if (!location.startsWith('http')) {
                        currentUrl = new URL(location, currentUrl).href;
                    } else {
                        currentUrl = location;
                    }
                    
                    redirectChain.push(currentUrl);
                    redirectCount++;
                    continue;
                }
            }
            
            // Check for JavaScript redirects in HTML content
            if (response.status === 200 && response.headers['content-type']?.includes('text/html')) {
                const content = response.data;
                const jsRedirectPatterns = [
                    /window\.location\.href\s*=\s*["']([^"']+)["']/gi,
                    /window\.location\s*=\s*["']([^"']+)["']/gi,
                    /location\.href\s*=\s*["']([^"']+)["']/gi,
                    /location\s*=\s*["']([^"']+)["']/gi,
                    /document\.location\s*=\s*["']([^"']+)["']/gi,
                    /window\.location\.replace\s*\(\s*["']([^"']+)["']\s*\)/gi,
                    /<meta[^>]+http-equiv=["']refresh["'][^>]+url=([^"'\s>]+)/gi
                ];
                
                let foundRedirect = false;
                for (const pattern of jsRedirectPatterns) {
                    const matches = [...content.matchAll(pattern)];
                    if (matches.length > 0) {
                        for (const match of matches) {
                            const jsUrl = match[1];
                            // Skip obviously non-redirect URLs
                            if (['javascript:', 'mailto:', '#', 'void(0)'].some(skip => jsUrl.toLowerCase().includes(skip))) {
                                continue;
                            }
                            
                            // Handle relative URLs
                            if (jsUrl.startsWith('/')) {
                                const urlObj = new URL(currentUrl);
                                currentUrl = `${urlObj.protocol}//${urlObj.host}${jsUrl}`;
                            } else if (!jsUrl.startsWith('http')) {
                                currentUrl = new URL(jsUrl, currentUrl).href;
                            } else {
                                currentUrl = jsUrl;
                            }
                            
                            redirectChain.push(currentUrl);
                            redirectCount++;
                            foundRedirect = true;
                            break;
                        }
                        if (foundRedirect) break;
                    }
                }
                
                if (!foundRedirect) {
                    break; // No more redirects found
                }
            } else {
                break; // No redirect and not HTML
            }
        } catch (error) {
            // If GET fails, try HEAD request
            try {
                const response = await axios.head(currentUrl, {
                    headers,
                    maxRedirects: 0,
                    validateStatus: (status) => status < 400,
                    timeout: 10000
                });
                
                if ([301, 302, 303, 307, 308].includes(response.status)) {
                    const location = response.headers.location;
                    if (location) {
                        if (location.startsWith('/')) {
                            const urlObj = new URL(currentUrl);
                            currentUrl = `${urlObj.protocol}//${urlObj.host}${location}`;
                        } else if (!location.startsWith('http')) {
                            currentUrl = new URL(location, currentUrl).href;
                        } else {
                            currentUrl = location;
                        }
                        
                        redirectChain.push(currentUrl);
                        redirectCount++;
                        continue;
                    }
                }
                break;
            } catch (headError) {
                break; // Both GET and HEAD failed
            }
        }
    }
    
    // Clean up tracking parameters from final URL
    const trackingParams = new Set([
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'fbclid', 'gclid', 'msclkid', 'twclid', 'li_fat_id',
        '_ga', '_gl', 'mc_cid', 'mc_eid', 'mkt_tok',
        'ref', 'referrer', 'source', 'campaign',
        'igshid', 'ncid', 'cmpid', 'WT.mc_id'
    ]);
    
    try {
        const urlObj = new URL(currentUrl);
        const params = new URLSearchParams(urlObj.search);
        
        // Remove tracking parameters
        for (const [key] of params) {
            if (trackingParams.has(key.toLowerCase())) {
                params.delete(key);
            }
        }
        
        urlObj.search = params.toString();
        currentUrl = urlObj.toString();
    } catch (error) {
        // If URL parsing fails, return as-is
        console.warn(`Failed to clean tracking parameters from URL: ${error.message}`);
    }
    
    return {
        originalUrl: url,
        finalUrl: currentUrl,
        redirectCount,
        redirectChain,
        maxRedirectsReached: redirectCount >= maxRedirects
    };
}

/**
 * Determine file extension from URL or content type
 * @param {string} url - URL to analyze
 * @param {string} contentType - Content-Type header value
 * @returns {string} - File extension with dot (e.g., '.pdf')
 */
function determineFileExtension(url, contentType = '') {
    const urlLower = url.toLowerCase();
    
    // First check URL extension
    if (urlLower.endsWith('.pdf')) return '.pdf';
    if (urlLower.endsWith('.docx') || urlLower.endsWith('.doc')) return '.docx';
    if (urlLower.endsWith('.pptx') || urlLower.endsWith('.ppt')) return '.pptx';
    if (urlLower.endsWith('.xlsx') || urlLower.endsWith('.xls')) return '.xlsx';
    if (urlLower.endsWith('.csv')) return '.csv';
    if (urlLower.endsWith('.json')) return '.json';
    if (urlLower.endsWith('.xml')) return '.xml';
    if (urlLower.endsWith('.epub')) return '.epub';
    if (urlLower.endsWith('.zip')) return '.zip';
    if (urlLower.match(/\.(jpg|jpeg|png|gif|bmp|tiff|webp)$/)) return '.jpg';
    if (urlLower.match(/\.(mp3|wav|m4a|aac)$/)) return '.mp3';
    if (urlLower.endsWith('.txt')) return '.txt';
    
    // If no extension found in URL, check content-type header
    if (contentType) {
        const ct = contentType.toLowerCase();
        if (ct.includes('pdf') || ct === 'application/pdf') return '.pdf';
        if (ct.includes('wordprocessingml') || ct === 'application/msword') return '.docx';
        if (ct.includes('presentationml') || ct === 'application/vnd.ms-powerpoint') return '.pptx';
        if (ct.includes('spreadsheetml') || ct === 'application/vnd.ms-excel') return '.xlsx';
        if (ct === 'text/csv') return '.csv';
        if (ct === 'application/json') return '.json';
        if (ct.includes('xml')) return '.xml';
        if (ct === 'application/epub+zip') return '.epub';
        if (ct === 'application/zip') return '.zip';
        if (ct.startsWith('image/')) return '.jpg';
        if (ct.startsWith('audio/')) return '.mp3';
        if (ct === 'text/plain') return '.txt';
    }
    
    return '.html'; // Default to HTML
}

module.exports = {
    isHtmlContent,
    extractArticleContent,
    cleanHtml,
    fetchWithBrowserFallback,
    dereferenceUrl,
    determineFileExtension
};