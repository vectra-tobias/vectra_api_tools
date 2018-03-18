import json
import requests
import warnings

# requests.packages.urllib3.disable_warnings()
warnings.filterwarnings('always', '.*', PendingDeprecationWarning)


def request_error_handler(func):
    def request_handler(self, **kwargs):
        response = func(self, **kwargs)

        if response.status_code in [200, 201]:
            return response
        else:
            # TODO implement exception class to more gracefully handle exception
            raise Exception(response.status_code, response.content)

    return request_handler


def validate_api_v2(func):
    def api_validator(self, **kwargs):
        if self.version == 2:
            return func(self, **kwargs)
        else:
            raise NotImplementedError('Method only accessible via v2 of API')

    return api_validator


def deprecation(message):
    warnings.warn(message, PendingDeprecationWarning)


def param_deprecation(key):
    message = '{0} will be deprecated with Vectra API v1 which will be annouced in an upcoming release'.format(key)
    warnings.warn(message, PendingDeprecationWarning)


class VectraClient(object):

    def __init__(self, url=None, token=None, user=None, password=None, verify=False):
        """
        Initialize Vectra client
        :param url: IP or hostname of Vectra brain (ex https://www.example.com) - required
        :param token: API token for authentication when using API v2*
        :param user: Username to authenticate to Vectra brain when using API v1*
        :param password: Password when using username to authenticate using API v1*
        :param verify: Verify SSL (default: False) - optional
        :rtype: requests object
        *Either token or user are required
        """
        self.url = url
        self.version = 2 if token else 1
        self.verify = verify

        if token:
            self.url = '{url}/api/v2'.format(url=url)
            self.headers = {
                'Authorization': "Token " + token.strip(),
            }
        elif user and password:
            self.url = '{url}/api'.format(url=url)
            self.auth = (user, password)
            deprecation('Deprecation of the Vectra API v1 will be announced in an upcoming release. Migrate to API v2'
                        ' when possible')
        else:
            raise RuntimeError("At least one form of authentication is required. Please provide a token or username"
                               " and password")

    @staticmethod
    def _generate_host_params(args):
        """
        Generate query parameters for hosts based provided args
        :param args: dict of keys to generate query params
        :rtype: dict
        """
        params = {}
        valid_keys = ['active_traffic', 'c_score', 'c_score_gte', 'certainty', 'certainty_gte', 'fields',
                      'has_active_traffic', 'include_detection_summaries', 'is_key_asset', 'is_targeting_key_asset',
                      'key_asset', 'last_source', 'mac_address', 'name', 'ordering', 'page', 'page_size', 'state',
                      't_score', 't_score_gte', 'tags', 'threat', 'threat_gte', 'targets_key_asset']
        deprecated_keys = ['c_score', 'c_score_gte', 'key_asset', 't_score', 't_score_gte', 'targets_key_asset']
        for k, v in args.items():
            if k in valid_keys and v is not None: params[k] = v
            if k in deprecated_keys: param_deprecation(k)
        return params

    @staticmethod
    def _generate_detection_params(args):
        """
        Generate query parameters for detections based provided args
        :param args: dict of keys to generate query params
        :rtype: dict
        """
        params = {}
        valid_keys = ['c_score', 'c_score_gte', 'category', 'certainty', 'certainty_gte', 'detection', 'detection_type',
                      'detection_category', 'fields', 'host_id', 'is_targeting_key_asset', 'is_triaged', 'ordering',
                      'page', 'page_size', 'src_ip', 'state', 't_score', 't_score_gte', 'tags', 'targets_key_asset',
                      'threat', 'threat_gte']
        deprecated_keys = ['c_score', 'c_score_gte', 'category', 't_score', 't_score_gte', 'targets_key_asset']
        for k, v in args.items():
            if k in valid_keys and v is not None: params[k] = v
            if k in deprecated_keys: param_deprecation(k)
        return params

    @request_error_handler
    def get_hosts(self, **kwargs):
        """
        Query all hosts - all parameters are optional
        :param active_traffic: host has active traffic (bool)
        :param c_score: certainty score (int) - will be removed with deprecation of v1 of api
        :param c_score_gte: certainty score greater than or equal to (int) - will be removed with deprecation of v1 of api
        :param certainty: certainty score (int)
        :param certainty_gte: certainty score greater than or equal to (int)
        :param fields: comma separated string of fields to be filtered and returned
        :param has_active_traffic: host has active traffic (bool)
        :param include_detection_summaries: include detection summary in response (bool)
        :param is_key_asset: host is key asset (bool)
        :param is_targeting_key_asset: host is targeting key asset (bool)
        :param key_asset: host is key asset (bool) - will be removed with deprecation of v1 of api
        :param last_source: registered ip address of host
        :param mac_address: registered mac address of host
        :param name: registered name of host
        :param ordering: field to use to order response
        :param page: page number to return (int)
        :param page_size: number of object to return in repsonse (int)
        :param state: state of host (active/inactive)
        :param t_score: threat score (int) - will be removed with deprecation of v1 of api
        :param t_score_gte: threat score greater than or equal to (int) - will be removed with deprection of v1 of api
        :param tags: tags assigned to host
        :param targets_key_asset: host is targeting key asset (bool)
        :param threat: threat score (int)
        :param threat_gte: threat score greater than or equal to (int)
        """

        if self.version == 2:
            return requests.get('{url}/hosts'.format(url=self.url), headers=self.headers,
                                params=self._generate_host_params(kwargs), verify=self.verify)
        else:
            return requests.get('{url}/hosts'.format(url=self.url), auth=self.auth, 
                                params=self._generate_host_params(kwargs), verify=self.verify)

    def get_all_hosts(self, **kwargs):
        """
        Generator to retrieve all hosts page by page
        Same parameters as get_host()
        """
        resp = self.get_hosts(**kwargs)
        yield resp
        while resp.json()['next']:
            url = resp.json()['next']
            path = url.replace(self.url, '')
            resp = self.custom_endpoint(path=path)
            yield resp

    @request_error_handler
    def get_host_by_id(self, host_id=None, **kwargs):
        """
        Get host by id
        :param host_id: host id - required
        :param fields: comma separated string of fields to be filtered and returned - optional
        """
        if not host_id:
            raise Exception('Host id required')

        if self.version == 2:
            return requests.get('{url}/hosts/{id}'.format(url=self.url, id=host_id), headers=self.headers,
                                params=self._generate_host_params(kwargs), verify=self.verify)
        else:
            return requests.get('{url}/hosts/{id}'.format(url=self.url, id=host_id), auth=self.auth,
                                params=self._generate_host_params(kwargs), verify=self.verify)

    @validate_api_v2
    @request_error_handler
    def set_key_asset(self, host_id=None, set=True):
        """
        (Un)set host as key asset
        :param id: id of host needing to be set - required
        :param set: set flag to true if setting host as key asset
        """

        if not host_id:
            raise ValueError('Host id required')

        headers = self.headers
        headers.update({
            'Content-Type': 'application/x-www-form-urlencoded'
        })

        if set:
            payload = 'key_asset=True'
        else:
            payload = 'key_asset=False'

        return requests.patch('{url}/hosts/{id}'.format(url=self.url, id=host_id), headers=headers, data=payload,
                              verify=self.verify)

    @validate_api_v2
    @request_error_handler
    def get_host_tags(self, host_id=None):
        """
        Get host ags
        :param host_id: 
        """
        return requests.get('{url}/tagging/host/{id}'.format(url=self.url, id=host_id), headers=self.headers,
                            verify=False)

    @validate_api_v2
    @request_error_handler
    def set_host_tags(self, host_id=None, tags=[], append=False):
        """
        Set host tags
        :param host_id: 
        :param tags: list of tags to add to host
        :param append: overwrites existing list if set to False, appends to existing tags if set to True 
        Set to empty list to clear tags (default: False)
        :return: 
        """
        if append and type(tags) == list:
            current_list = self.get_host_tags(host_id=host_id).json()['tags']
            payload = {
                "tags": current_list + tags
            }
        elif type(tags) == list:
            payload = {
                "tags": tags
            }
        else:
            raise TypeError('tags must be of type list')

        headers = self.headers
        headers.update({
            'Content-Type': "application/json",
            'Cache-Control': "no-cache"
        })

        return requests.patch('{url}/tagging/host/{id}'.format(url=self.url, id=host_id), headers=headers,
                              data=json.dumps(payload), verify=self.verify)

    @request_error_handler
    def get_detections(self, **kwargs):
        """
        Query all detections - all paramters are optional
        :param c_score: certainty score (int) - will be removed with deprecation of v1 of api
        :param c_score_gte: certainty score greater than or equal to (int) - will be removed with deprecation of v1 of api
        :param category: detection category - will be removed with deprecation of v1 of api
        :param certainty: certainty score (int)
        :param certainty_gte: certainty score greater than or equal to (int)
        :param detection:
        :param detection_type: detection type
        :param detection_category: detection category
        :param fields: comma separated string of fields to be filtered and returned
        :param host_id: detection id (int)
        :param is_targeting_key_asset: detection is targeting key asset (bool)
        :param is_triaged: detection is triaged
        :param ordering: field used to sort response
        :param src_ip: source ip address of host attributed to detection
        :param state: state of detection (active/inactive)
        :param t_score: threat score (int) - will be removed with deprecation of v1 of api
        :param t_score_gte: threat score is greater than or equal to (int) - will be removed with deprecation of v1 of api
        :param tags: tags assigned to detection
        :param targets_key_asset: detection targets key asset (bool) - will be removed with deprecation of v1 of api
        :param threat: threat score (int)
        :param threat_gte threat score is greater than or equal to (int)
        """

        if self.version == 2:
            return requests.get('{url}/detections'.format(url=self.url), headers=self.headers,
                                params=self._generate_detection_params(kwargs), verify=self.verify)
        else:
            return requests.get('{url}/detections'.format(url=self.url), auth=self.auth, 
                                params=self._generate_detection_params(kwargs), verify=self.verify)

    def get_all_detections(self, **kwargs):
        """
        Generator to retrieve all detections page by page
        Same parameters as get_detections()
        """
        resp = self.get_detections(**kwargs)
        yield resp
        while resp.json()['next']:
            url = resp.json()['next']
            path = url.replace(self.url, '')
            resp = self.custom_endpoint(path=path).json()
            yield resp

    @request_error_handler
    def get_detection_by_id(self, detection_id=None, **kwargs):
        """
        Get detection by id
        :param detection_id: detection id - required
        :param fields: comma separated string of fields to be filtered and returned
        """
        if not detection_id:
            raise Exception('Detection id required')

        if self.version == 2:
            return requests.get('{url}/detections/{id}'.format(url=self.url, id=detection_id), headers=self.headers,
                                params=self._generate_detection_params(kwargs), verify=self.verify)
        else:
            return requests.get('{url}/detections/{id}'.format(url=self.url, id=detection_id), auth=self.auth,
                                params=self._generate_detection_params(kwargs), verify=self.verify)

    @validate_api_v2
    @request_error_handler
    def get_detection_tags(self, detection_id=None):
        """
        Get detection tags
        :param detection_id:
        """
        return requests.get('{url}/tagging/detection/{id}'.format(url=self.url, id=detection_id), headers=self.headers,
                            verify=False)

    @validate_api_v2
    @request_error_handler
    def set_detection_tags(self, detection_id=None, tags=[], append=False):
        """
        Set  detection tags
        :param detection_id: 
        :param tags: list of tags to add to detection
        :param append: overwrites existing list if set to False, appends to existing tags if set to True 
        Set to empty list to clear all tags (default: False)
        """
        if append and type(tags) == list:
            current_list = self.get_detection_tags(detection_id=detection_id).json()['tags']
            payload = {
                "tags": current_list + tags
            }
        elif type(tags) == list:
            payload = {
                "tags": tags
            }
        else:
            raise TypeError('tags must be of type list')

        headers = self.headers
        headers.update({
            'Content-Type': "application/json",
            'Cache-Control': "no-cache"
        })

        return requests.patch('{url}/tagging/detection/{id}'.format(url=self.url, id=detection_id), headers=headers,
                              data=json.dumps(payload), verify=self.verify)

    @validate_api_v2
    @request_error_handler
    def get_proxies(self, proxy_id=None):
        if proxy_id:
            return requests.get('{url}/proxies/{id}'.format(url=self.url, id=proxy_id), headers=self.headers,
                                verify=self.verify)
        else:
            return requests.get('{url}/proxies'.format(url=self.url), headers=self.headers, verify=self.verify)

    @validate_api_v2
    @request_error_handler
    def add_proxy(self, host=None, enable=True):
        headers = self.headers
        headers.update({
            "Content-Type": "application/json"
        })

        payload = {
            "proxy": {
                "address": host,
                "considerProxy": enable
            }
        }

        return requests.post('{url}/proxies'.format(url=self.url), json=payload, headers=headers, verify=self.verify)

    @validate_api_v2
    @request_error_handler
    def update_proxy(self, proxy_id=None, address=None, enable=True):
        headers = self.headers
        headers.update({
            "Content-Type": "application/json"
        })

        proxy = self.get_proxies(proxy_id=proxy_id).json()['proxies']
        payload = {
            "proxy": {
                "address": address if address else proxy['ip'],
                "considerProxy": enable
            }
        }

        return requests.patch('{url}/proxies/{id}'.format(url=self.url, id=proxy_id), json=payload, headers=headers,
                              verify=self.verify)

    @validate_api_v2
    @request_error_handler
    def create_feed(self, name=None, category=None, certainty=None, itype=None, duration=None):
        """
        Creates new threat feed
        ***Values for category, type, and certainty are case sensitive***
        :param name: name of threat feed
        :param category: category that detection will register. supported values are lateral, exfil, and cnc
        :param certainty: certainty applied to detection. Supported values are Low, Medium, High
        :param itype: indicator type - supported values are Anonymize, Exfiltration, Malware Artifacts, and Watchlist
        :param duration: days that the threat feed will be applied
        :returns: request object
        """

        payload = {
            "threatFeed": {
                "name": name,
                "defaults": {
                    "category": category,
                    "certainty": certainty,
                    "indicatorType": itype,
                    "duration": duration
                }
            }
        }

        headers = self.headers
        headers.update({
            'Content-Type': "application/json",
            'Cache-Control': "no-cache"
        })

        return requests.post('{url}/threatFeeds'.format(url=self.url), data=json.dumps(payload), headers=headers,
                             verify=self.verify)

    @validate_api_v2
    @request_error_handler
    def delete_feed(self, feed_id=None):
        """
        Deletes threat feed from Vectra
        :param feed_id: id of threat feed (returned by get_feed_by_name())
        """
        return requests.delete('{url}/threatFeeds/{id}'.format(url=self.url, id=feed_id),
                               headers=self.headers, verify=self.verify)

    @validate_api_v2
    @request_error_handler
    def get_feeds(self):
        """
        Gets list of currently configured threat feeds
        """
        return requests.get('{url}/threatFeeds'.format(url=self.url), headers=self.headers, verify=self.verify)

    @validate_api_v2
    def get_feed_by_name(self, name=None):
        """
        Gets configured threat feed by name and returns id (used in conjunction with updating and deleting feeds)
        :param name: name of threat feed
        """
        try:
            response = requests.get('{url}/threatFeeds'.format(url=self.url), headers=self.headers, verify=self.verify)
        except requests.ConnectionError:
            raise Exception('Unable to connect to remote host')

        if response.status_code == 200:
            for feed in response.json()['threatFeeds']:
                if feed['name'].lower() == name.lower():
                    return feed['id']
        else:
            raise Exception(response.status_code, response.content)

    @validate_api_v2
    @request_error_handler
    def post_stix_file(self, feed_id=None, stix_file=None):
        """
        Uploads STIX file to new threat feed or overwrites STIX file in existing threat feed
        :param feed_id: id of threat feed (returned by get_feed_by_name)
        :param stix_file: stix filename
        """
        return requests.post('{url}/threatFeeds/{id}'.format(url=self.url, id=feed_id), headers=self.headers,
                             files={'file': open(stix_file)}, verify=self.verify)

    @request_error_handler
    def custom_endpoint(self, path=None, **kwargs):
        if not str(path).startswith('/'):
            path = '/' + str(path)

        params = {}
        for k, v in kwargs.items():
            params[k] = v

        if self.version == 2:
            return requests.get(self.url + path, headers=self.headers, params=params, verify=self.verify)
        else:
            return requests.get(self.url + path, auth=self.auth, params=params, verify=self.verify)