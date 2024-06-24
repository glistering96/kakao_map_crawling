import json
import logging
import time
from pathlib import Path
from time import sleep
import pandas as pd
from scipy import stats
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.chrome.options import Options
import numpy as np

class KakaoMapCrawler:
    def __init__(self):
        self.url = 'https://map.kakao.com/'
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # 헤드리스 모드 활성화
        
        self.driver = webdriver.Chrome(options=chrome_options)
        
        self.result_dict = {'place_info': []}
        self.refiner = ResultRefiner()
        self.logger = self.setup_logger()
        self.error_count = 0
        self.page = 1
        self.page2 = 0

    def setup_logger(self):
        path = Path("logs/")
        if not path.exists():
            path.mkdir(parents=True)

        logger = logging.getLogger(__name__)
        formatter = logging.Formatter('[%(asctime)s][%(levelname)s|%(filename)s:%(lineno)s] >> %(message)s')
        file_handler = logging.FileHandler(f'logs/{time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())}.log')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        logger.setLevel(logging.INFO)
        return logger

    def time_wait(self, num, code):
        try:
            wait = WebDriverWait(self.driver, num).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, code)))
        except Exception as e:
            self.logger.warning(f'{code} 태그를 찾지 못하였습니다: {e}')
            self.driver.quit()
        return wait

    def append_place_info(self):
        sleep(0.2)
        place_lst = self.driver.find_elements(By.CSS_SELECTOR, '.placelist > .PlaceItem')
        names = self.driver.find_elements(By.CSS_SELECTOR, '.head_item > .tit_name > .link_name')
        types = self.driver.find_elements(By.CSS_SELECTOR, '.head_item > .subcategory')
        address_list = self.driver.find_elements(By.CSS_SELECTOR, '.info_item > .addr')
        ratings_lst = self.driver.find_elements(By.CSS_SELECTOR, '.rating > .score')

        for index in range(len(place_lst)):
            self.logger.info(index)
            address = address_list[index].find_elements(By.CSS_SELECTOR, 'p')
            restaurant_name = names[index].text
            restaurant_type = types[index].text
            addr1 = address[0].text
            rating = ratings_lst[index].text
            if len(rating) > 0:
                score, num_records = rating.split("\n")
                score = float(score)
                num_records = int(num_records[:-1])
            else:
                score, num_records = -1, 0

            dict_temp = {
                'name': restaurant_name,
                'restaurant type': restaurant_type,
                'address': addr1,
                "rating": score,
                "num_rating_records": num_records
            }
            self.result_dict['place_info'].append(dict_temp)
            self.logger.info(f'{restaurant_name} ...완료')

    def crawl(self, keyword):
        file_dir = f"./data/{keyword}.csv"
        
        if self.find_in_cache(keyword):
            result = pd.read_csv(file_dir)
            return result
        
        self.driver.get(self.url)
        self.time_wait(5, 'div.box_searchbar > input.query')
        search = self.driver.find_element(By.CSS_SELECTOR, 'div.box_searchbar > input.query')
        search.send_keys(keyword)
        search.send_keys(Keys.ENTER)
        sleep(1)
        place_tab = self.driver.find_element(By.CSS_SELECTOR, '#info\\.main\\.options > li.option1 > a')
        place_tab.send_keys(Keys.ENTER)
        sleep(1)
        place_lst = self.driver.find_elements(By.CSS_SELECTOR, '.placelist > .PlaceItem')
        self.logger.info('[크롤링 시작...]')
        start = time.time()

        while True:
            try:
                self.page2 += 1
                self.logger.info(f"**** {self.page} ****")
                self.driver.find_element(By.XPATH, f'//*[@id="info.search.page.no{self.page2}"]').send_keys(Keys.ENTER)
                self.append_place_info()
                place_lst = self.driver.find_elements(By.CSS_SELECTOR, '.placelist > .PlaceItem')
                if len(place_lst) < 15:
                    break
                if not self.driver.find_element(By.XPATH, '//*[@id="info.search.page.next"]').is_enabled():
                    break
                if self.page2 % 5 == 0:
                    self.driver.find_element(By.XPATH, '//*[@id="info.search.page.next"]').send_keys(Keys.ENTER)
                    self.page2 = 0
                self.page += 1
            except Exception as e:
                self.error_count += 1
                self.logger.error(e)
                if self.error_count > 5:
                    break

        self.logger.info('[데이터 수집 완료]\n소요 시간 : ' + str(time.time() - start))
        self.driver.quit()
        self.logger.info("[데이터 저장 완료]")
        self.logger.info(f"에러 횟수 : {self.error_count}")
        

        
        result = self.refiner.get_result_df(self.result_dict)
        result.to_csv(file_dir, index=False)

            
        return result
            
    def find_in_cache(self, keyword):
        file = f"./data/{keyword}.csv"
        
        path = Path(file)
        
        if path.exists():
            return True
        
        else:
            return False
        
    def save_to_json(self):
        path = Path("data/")
        if not path.exists():
            path.mkdir(parents=True)
        with open(f'data/{self.keyword}.json', 'w', encoding='utf-8') as f:
            json.dump(self.result_dict, f, indent=4, ensure_ascii=False)

class ResultRefiner:
    def __init__(self) -> None:
        pass
    
    def get_result_df(self, result_dict):
        df = pd.DataFrame(result_dict['place_info'])
        df = df.drop_duplicates(subset=['name'])
        df['rating_range'] = df['rating'].apply(int)
        df['rating_records_range'] = df['num_rating_records'].apply(lambda x: self.rating_record_range(x))
        df = df[['name', 'restaurant type', 'address', 'rating', "rating_range", 'num_rating_records', "rating_records_range"]].copy()
        df = df[df['num_rating_records'] > 0].copy()
        no_ratings = df[df['num_rating_records'] <= 0].copy()
        overall_mean = (df['rating']*df['num_rating_records']).sum() / df['num_rating_records'].sum()
        df[['p_value']] = df.apply(self.calculate_confidence_interval_and_p_value, overall_mean=overall_mean, axis=1)
        df = df.sort_values(by=['rating', 'p_value'], ascending = (False,True))
        result = pd.concat([df, no_ratings])
        return result
        

    def rating_record_range(self, x):
        if x < 10:
            return '0~10'
        elif x < 30:
            return '10~30'
        
        elif x < 50:
            return '30~50'
        
        else:
            return '50+'
        
        
    def calculate_confidence_interval_and_p_value(self, row, overall_mean):
        mean = row['rating']
        n = row['num_rating_records']
        
        # 별점의 표준 편차를 1.5로 가정 (1~5 사이 값에서의 분포)
        std_dev = 1.5
        
        # 표준 오차 계산
        se = std_dev / (np.sqrt(n) + 1e-8)
        
        # 95% 신뢰 구간 계산
        confidence_level = 0.95
        z_score = stats.norm.ppf((1 + confidence_level) / 2)
        margin_of_error = z_score * se
        confidence_interval = (mean - margin_of_error, mean + margin_of_error)
        
        # p-value 계산 (양측 검정)
        z = (mean - overall_mean) / se
        p_value = 2 * (1 - stats.norm.cdf(abs(z)))
        
        return pd.Series({
            'p_value': round(p_value, 5)
        })


        
        
if __name__ == "__main__":
    keyword = input("Enter the keyword to search: ")
    crawler = KakaoMapCrawler()
    crawler.crawl(keyword)
