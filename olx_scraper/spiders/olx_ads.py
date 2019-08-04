# -*- coding: utf-8 -*-
import urllib.parse as ups
import scrapy, re, requests, json, time

# def get_geo_coordinates(location_string, return_str=False):
#     url = "https://us1.locationiq.com/v1/search.php"

#     data = {
#         'key': '43ca768ffb16fa',
#         'q': location_string,
#         'format': 'json'
#     }
#     try:
#         response = requests.get(url, params=data)
#         if not response: raise Exception
#         geo_data = json.loads(response.text)[0]
#         coord = [geo_data['lat'], geo_data['lon']]
#         # print(coord)
#         return ",".join(coord) if return_str else coord
#     except:
#         return [0,0] # lat, lon



        

class OlxAdsSpider(scrapy.Spider):
    name = 'olx_public_ads'
    allowed_domains = ['olxliban.com']
    start_urls = [
        "https://olxliban.com/changelang/?lang=en&l=https://olxliban.com/en",        
        'http://olxliban.com/en/ads'
    ]
    page_counter = 1
    needed_fields = [
                    'regionId',
                    'regionName',
                    'cityName',
                    'categoryLevel1Name',
                    'categoryLevel2Name',
                    'categoryLevel3Name',
                    'itemId',
                    'sellerId',
                    'imagesCount',
                    'creationDate',
                    'itemPrice']

    # ['nw', 'siteUrl', 'environment', 'language', 'platformType', 'regionId', 
    # 'regionName', 'cityId', 'cityName', 'categoryLevel1Id', 'categoryLevel1Name', 
    # 'categoryLevel2Id', 'categoryLevel2Name', 'categoryLevel3Id', 'categoryLevel3Name',
    # 'trackPage', 'itemId', 'sellerId', 'sellerType', 'imagesCount', 'creationDate', 'itemPrice', 't']

    all_locations = {}    

    def get_geo_coordinates(self, location_string, separator, return_str=False):
        try:
            coord = self.all_locations.get(location_string, None)
            if not coord:
                geo_api_data = { 'key': self.settings['GEOLOCCATION_API_KEY'], 'format': 'json' }
                geo_api_data['q'] = location_string + ", " + self.settings['COUNTRY_NAME']
                response = requests.get(self.settings['GEOLOCCATION_API_URL'], params=geo_api_data)
                if not response: 
                    # it might failed because of distinct name, we will retry with only city and country name
                    geo_api_data['q'] = location_string.split(separator)[0]  + ", " + self.settings['COUNTRY_NAME']
                    time.sleep(1)
                    response = requests.get(self.settings['GEOLOCCATION_API_URL'], params=geo_api_data)
                    print("Try to find location of "+geo_api_data['q'])
                    if not response: 
                        self.all_locations[location_string] = [0,0]
                        raise Exception("Getting Location Failed for %s"%location_string)

                geo_data = json.loads(response.text)
                # we are checking if the found coordinates are within the boundaries of the
                # alpha = self.settings['GEO_COORD_TOLERANCE'] + 0.1
                # [T, D, R, L] = [alpha + self.settings['GEO_TOP_LIMIT'],
                #                 alpha + self.settings['GEO_DOWN_LIMIT'],
                #                 alpha + self.settings['GEO_RIGHT_LIMIT'],
                #                 alpha + self.settings['GEO_LEFT_LIMIT']]
                # found_coords = [[d['lat'], d['lon']] for d in geo_data if (D <= float(d['lat']) <= T) and (L <= float(d['lon']) <= R)]
                found_coords = [[d['lat'], d['lon']] for d in geo_data]
                coord = found_coords[0] # there may be more than adjacent valid location (in lebanon)
                # if found_coords is empty, it will raise an exception and return [0,0]
                # print(coord)
                self.all_locations[location_string] = coord
            return ",".join(coord) if return_str else coord
        except IndexError:
            msg = "No Location Found for: %s"%location_string
            self.logger.error(msg)
            print(msg)
            
            return [0,0] # lat, lon
        except Exception as ex:
            print(ex)
            self.logger.error(str(ex))
            return [0,0] # lat, lon

    def parse(self, response):
        # try:
        for ad_link in response.css("a.ads__item__ad--title::attr(href)"):
            yield response.follow(ad_link, self.parse_ad_info)
        # next_page = 
        self.page_counter += 1
        next_page_url = self.start_urls[1]+"/?page=%s"%str(self.page_counter)
        print(next_page_url)
        yield scrapy.Request(next_page_url, self.parse)
        # max_page = response.css('span.item.fleft::nth-child a').get() # not worked
        # next_page = response.css('span.item.fleft a::attr(href)').get()
        # if next_page:
        #     yield response.follow(next_page, self.parse)


    def parse_ad_info(self, response):
        def extract_by_css(selector):
            return response.css(selector).get(default='').strip()
        try:

            ad_info = {
                    'adCode': response.request.url.split("-")[-1].split(".")[0],
                    'title': extract_by_css("h1.brkword.lheight28::text"),
                    'sellerName': extract_by_css("p.user-box__info__name::text"),
                    'phone': extract_by_css("ul#contact_methods > li > div > strong::text"),
                    'viewCount': extract_by_css("div#offerbottombar > div:nth-child(3) > strong::text"),
                    'description': extract_by_css("#textContent > p::text"),
                    'itemPriceNegotiable': 1 if extract_by_css("#offeractions > div.pdingbott20 > div.pricelabel.tcenter > small::text") else 0,
                    # 'relatedAds'
                    'location': extract_by_css("span.show-map-link.cpointer>strong::text"),
                    # 'price': extract_by_css("div.pricelabel.tcenter:nth-child(3)")
                }
            # ad_date_id = extract_by_css("div.clr.offerheadinner.pding15.pdingright20 > p > small > span")
            # # Added					at 15:22, 9 July 2019, Ad ID: 106504759
            # ad_date_id_data = re.match(r"Added +at +(?P<date>[0-9:], [0-9a-zA-Z]), +Ad ID: +(?P<id>\d+)", ad_date_id).groupdict()
            # ad_info['published_date'] = ad_date_id_data['date']
            # ad_info['ad_id'] = ad_date_id_data['id']
            date_id_text = extract_by_css("div.clr.offerheadinner.pding15.pdingright20 > p > small > span::text")
            # print(date_id_text)
            data = re.match(r"Added[\s\t]*at *(?P<time>[0-9:]+),", date_id_text)
            ad_info['creationTime'] = data.groupdict().get('time', None) if data else None
            
            no_script_tag = response.xpath("/html/head/noscript").extract_first()
            if no_script_tag:
                data_check = re.search("src=\"(.*)\"", no_script_tag)
                data_url = data_check.group(1) # return url that contains all data
                # extra_data = dict(map(lambda chunk: tuple(chunk.split("=")), data_url.split("&")[4:-1])) # return tuples
                qry = ups.urlparse(data_url).query
                extract_data = ups.parse_qs(qry)
                ad_info.update({k:extract_data.get(k, [None])[0] for k in self.needed_fields})
                # location_string = ad_info['location']
                location_string = "{}, {}".format(ad_info['cityName'], ad_info['regionName'])
                [ad_info['location_latitude'], ad_info['location_longitude']] = self.get_geo_coordinates(location_string, ",")
            yield ad_info
        except Exception as ex:
            print(ex)
            return