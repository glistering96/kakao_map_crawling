import json
import logging
from pathlib import Path
import time
from time import sleep

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# --크롬창을 숨기고 실행-- driver에 options를 추가해주면된다
# options = webdriver.ChromeOptions()
# options.add_argument('headless')

# logger path
path = Path("logs/")

if not path.exists():
    path.mkdir(parents=True)
    
# logger 생성
logger = logging.getLogger(__name__)

formatter = logging.Formatter('[%(asctime)s][%(levelname)s|%(filename)s:%(lineno)s] >> %(message)s')

# 현재 시간 (초단위 까지만) 기준으로 file handler 생성
# 이때 파일이름은 "yyyy-mm-dd hh:mm:ss.log"
file_handler = logging.FileHandler(f'logs/{time.strftime("%Y-%m-%d %H-%M-%S", time.localtime())}.log')

file_handler.setFormatter(formatter)

# logger에 file handler 추가
logger.addHandler(file_handler)   

url = 'https://map.kakao.com/'
driver = webdriver.Chrome()  # 드라이버 경로
# driver = webdriver.Chrome('./chromedriver',chrome_options=options) # 크롬창 숨기기

# css 찾을때 까지 10초대기
def time_wait(num, code):
    try:
        wait = WebDriverWait(driver, num).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, code)))
    except:
        logger.warning(code, '태그를 찾지 못하였습니다.')
        driver.quit()
    return wait

# place_info 추가 및 출력
def append_place_info(result_dict):

    # network 지연시간 고려 텀 주기
    time.sleep(0.2)

    # 하단의 .placelist > .PlaceItem 등은 웹 페이지의 html tag를 직접 찾아야 함
    # 모르겠으면 김원준에게 질의
    
    # (3) 장소 목록
    place_lst = driver.find_elements(By.CSS_SELECTOR, '.placelist > .PlaceItem')
    
    # (4) 장소명
    names = driver.find_elements(By.CSS_SELECTOR, '.head_item > .tit_name > .link_name')

    # (5) 장소 유형
    types = driver.find_elements(By.CSS_SELECTOR, '.head_item > .subcategory')

    # (6) 주소
    address_list = driver.find_elements(By.CSS_SELECTOR, '.info_item > .addr')
    
    # (7) 별점
    ratings_lst = driver.find_elements(By.CSS_SELECTOR, '.rating > .score')

    for index in range(len(place_lst)):
        logger.info(index)
        
        address = address_list.__getitem__(index).find_elements(By.CSS_SELECTOR, 'p')
        
        restaurant_name = names[index].text
        logger.info(restaurant_name)

        restaurant_type = types[index].text
        logger.info(restaurant_type)

        addr1 = address.__getitem__(0).text
        logger.info(addr1)
        
        rating = ratings_lst[index].text
        if len(rating) > 0: # 일부 식당에 rating 정보가 없다면 text="" 임
            # 별점 정보가 있으면 "점수\n몇건" 형태의 텍스트로 존재함
            score, num_records =  rating.split("\n")
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

        result_dict['place_info'].append(dict_temp)
        logger.info(f'{restaurant_name} ...완료')


driver.get(url)
key_word = '신당역 음식점'  # 검색어

# css를 찾을때 까지 5초 대기
time_wait(5, 'div.box_searchbar > input.query')

# (1) 검색창 찾기
search = driver.find_element(By.CSS_SELECTOR, 'div.box_searchbar > input.query')
search.send_keys(key_word)  # 검색어 입력
search.send_keys(Keys.ENTER)  # 엔터버튼 누르기

sleep(1)

# (2) 장소 탭 클릭
place_tab = driver.find_element(By.CSS_SELECTOR, '#info\.main\.options > li.option1 > a')
place_tab.send_keys(Keys.ENTER)

sleep(1)

# 장소 리스트
place_lst = driver.find_elements(By.CSS_SELECTOR, '.placelist > .PlaceItem')

# result dict 생성
result_dict = {'place_info': []}

# 시작시간
start = time.time()
logger.info('[크롤링 시작...]')

# 페이지 리스트만큼 크롤링하기
page = 1    # 현재 크롤링하는 페이지가 전체에서 몇번째 페이지인지
page2 = 0   # 1 ~ 5번째 중 몇번째인지
error_cnt = 0

while 1:

    # 페이지 넘어가며 출력
    try:
        page2 += 1
        logger.info("****", page, "****")

                # (7) 페이지 번호 클릭
        driver.find_element(By.XPATH, f'//*[@id="info.search.page.no{page2}"]').send_keys(Keys.ENTER)

                # 장소 리스트 크롤링
        append_place_info(result_dict)

                # 해당 페이지 장소 리스트
        place_lst = driver.find_elements(By.CSS_SELECTOR, '.placelist > .PlaceItem')
                # 한 페이지에 장소 개수가 15개 미만이라면 해당 페이지는 마지막 페이지
        if len(place_lst) < 15:
            break
                # 다음 버튼을 누를 수 없다면 마지막 페이지
        if not driver.find_element(By.XPATH, '//*[@id="info.search.page.next"]').is_enabled():
            break

        # (8) 다섯번째 페이지까지 왔다면 다음 버튼을 누르고 page2 = 0으로 초기화
        if page2 % 5 == 0:
            driver.find_element(By.XPATH, '//*[@id="info.search.page.next"]').send_keys(Keys.ENTER)
            page2 = 0

        page += 1

    except Exception as e:
        error_cnt += 1
        logging.error(e)

        if error_cnt > 5:
            break

logger.info('[데이터 수집 완료]\n소요 시간 :', time.time() - start)
driver.quit()  # 작업이 끝나면 창을 닫는다.

# json 파일로 저장
path = Path("data/")

if not path.exists():
    path.mkdir(parents=True)

with open(f'data/{key_word}.json', 'w', encoding='utf-8') as f:
    json.dump(result_dict, f, indent=4, ensure_ascii=False)
    
logger.info("[데이터 저장 완료]")

logger.info("에러 횟수 :", error_cnt)