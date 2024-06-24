import streamlit as st
from modules import KakaoMapCrawler


def main():
    st.title("카카오 맵 별점 기반 식당 찾기")
    st.write("미식가에 빙의한 카카오 지도 이용자의 별점 후기 데이터를 기반으로 통계적으로 유의미한 식당들을 찾아서 보여줍니다.")
    st.write("주의) 카카오 지도의 검색 결과에 따라 일치하지 않는 지역의 식당이 포함되어 있을 수 있습니다.")
    keyword = st.text_input("찾고자 하는 지역의 식당을 최대한 자세히 입력해주세요: i.e., xx역 근처 식당", "서울숲역 근처 식당")

    if st.button("Start Crawling"):
        st.write("Crawling started...")
        crawler = KakaoMapCrawler()
        df = crawler.crawl(keyword)
        st.write("Crawling finished. Here are the results:")
        st.dataframe(df)
        

if __name__ == "__main__":
    main()