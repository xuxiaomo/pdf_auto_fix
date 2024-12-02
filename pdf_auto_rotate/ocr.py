import logging
import requests
import io
import base64

from .utils import singleton

@singleton
class BaiduOCR:
    def __init__(self, api_key, secret_key):
        self.API_KEY = api_key
        self.SECRET_KEY = secret_key
        self.token = self.get_access_token()
    
    def get_access_token(self):
        """获取百度AI的access_token"""
        url = "https://aip.baidubce.com/oauth/2.0/token"
        params = {
            "grant_type": "client_credentials", 
            "client_id": self.API_KEY, 
            "client_secret": self.SECRET_KEY
        }
        return str(requests.post(url, params=params).json().get("access_token"))

    def get_result_from_api(self, image, api_name):
        img_str = self._image_to_base64(image)

        url = f"https://aip.baidubce.com/rest/2.0/ocr/v1/{api_name}?access_token={self.token}"

        payload = {
            "image": img_str,
            "detect_direction": "true",
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json'
        }

        response = requests.post(url, headers=headers, data=payload)
        result = response.json()
        return result

    def get_result_from_api(self, image):
        api_list = [
            "general_basic",
            "general",
            "accurate_basic",
            "accurate",
            "webimage",
            "webimage_loc",
        ]

        for api in api_list:
            result = self.get_result_from_api(image, api)
            if result.get("direction") is not None:
                return result
            else:
                logging.warning(f"接口不可用: {api}, Error Code: {result.get('error_code')}, Error Message: {result.get('error_msg')}, 使用下一个接口")
                continue

        raise Exception("没有可用的OCR接口")

    def detect_orientation(self, image):
        """使用百度OCR检测图像方向"""
        result = self.get_result_from_api(image)
        
        if 'direction' in result:
            # 百度OCR返回的direction: 0:正向，1:逆时针90度，2:逆时针180度，3:逆时针270度
            direction_map = {
                0: 0,
                1: 90,
                2: 180,
                3: 270
            }
            angle = direction_map.get(result['direction'], 0)
            return angle, 1.0
        else:
            raise Exception("未检测到方向信息")

    def _image_to_base64(self, image):
        buffered = io.BytesIO()
        image.save(buffered, format="JPEG", quality=95)
        img_str = base64.b64encode(buffered.getvalue()).decode()
        return img_str