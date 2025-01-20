import streamlit as st
from enum import Enum


class SearchSource(Enum):
    ENR = ("Engineering News-Record (ENR)", "https://www.enr.com/")
    CD = ("Construction Dive", "https://www.constructiondive.com/")

    def __init__(self, title, url):
        self.title = title
        self.url = url
        self.checkbox_key = f"checkbox_{self.name}"


class SearchSourceList:
    def __init__(self):
        self.sources = [
            SearchSource.ENR,
            SearchSource.CD,
        ]

    def show_checkbox(self, st):
        for source in self.sources:
            st.checkbox(source.title, value=True, key=source.checkbox_key)

    def get_checked_sources(self, st):
        return [
            source
            for source in self.sources
            if st.session_state.get(source.checkbox_key, False)
        ]


searchlist = SearchSourceList()


def main():
    # 사이드바 체크리스트 추가
    with st.sidebar:
        st.header("뉴스 소스 선택")
        searchlist.show_checkbox(st)

    # 메인 페이지
    st.title("나의 Streamlit 애플리케이션")
    st.write("여기에 내용을 추가하세요.")

    # 선택된 뉴스 소스와 URL 표시
    for source in searchlist.get_checked_sources(st):
        st.write(f"{source.title}: {source.url}")


if __name__ == "__main__":
    main()
