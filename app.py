import streamlit as st
from enum import Enum
import json
import asyncio
from pathlib import Path
from urllib.parse import urlparse
import requests

keyword_finder_url = st.secrets["keyword-finder-url"]
report_maker_url = st.secrets["report-maker-url"]


keyword_logs = None


class TaskType(Enum):
    KEYWORD = "keyword"
    REPORT = "report"


class SearchSource(Enum):
    ENR = ("Engineering News-Record (ENR)", "enr", "https://www.enr.com/")
    CD = ("Construction Dive", "cd", "https://www.constructiondive.com/")

    def __init__(self, title, alias, url):
        self.title = title
        self.url = url
        self.checkbox_key = f"checkbox_{self.name}"
        self.alias = alias


class SearchSourceList:
    def __init__(self):
        self.sources = [
            SearchSource.ENR,
            SearchSource.CD,
        ]

    def show_checkbox(self, task_type: TaskType):
        for source in self.sources:
            st.checkbox(
                source.title, value=True, key=f"{task_type.value}_{source.checkbox_key}"
            )

    def get_checked_sources(self, task_type: TaskType):
        return [
            source
            for source in self.sources
            if st.session_state.get(f"{task_type.value}_{source.checkbox_key}", False)
        ]


class Settings:
    def __init__(self):
        self.period_options = [
            ("1일", 1),
            ("3일", 3),
            ("1주일", 7),
            ("2주일", 14),
            ("1개월", 30),
        ]
        self.date_key = "search_start_date"
        self.period_key = "search_period"

    def show_date_settings(self):
        selected_date = st.date_input(
            "검색 시작일",
            help="검색을 시작할 날짜를 선택하세요",
            key=self.date_key,
        )

        selected_period = st.selectbox(
            "검색 기간",
            options=[p[0] for p in self.period_options],
            index=0,
            help="검색할 기간을 선택하세요",
            key=self.period_key,
        )

    def get_search_params(self):
        selected_date = st.session_state.get(self.date_key)
        period_days = st.session_state.get(self.period_key)
        return {
            "start_date": selected_date.strftime("%Y-%m-%d"),
            "period_days": period_days,
        }

    def get_search_period(self):
        selected_date = st.session_state.get(self.date_key)
        selected_period = st.session_state.get(self.period_key)
        if selected_date is None or selected_period is None:
            return ""

        selected_days = next(
            p[1] for p in self.period_options if p[0] == selected_period
        )
        start_date = selected_date.replace(day=selected_date.day - selected_days + 1)
        end_date = selected_date
        if selected_days == 1:
            return end_date.strftime("%Y-%m-%d")
        else:
            return f"{start_date.strftime('%Y-%m-%d')}~{end_date.strftime('%Y-%m-%d')}"

    def get_search_button_text(self):
        return f"키워드 검색 시작 {self.get_search_period()}"


class KeywordLogs:
    def __init__(self):
        self.log_key = "response_logs"
        if self.log_key not in st.session_state:
            st.session_state[self.log_key] = []

    def add_log(self, data=None, error_message=None, **kwargs):
        from datetime import datetime

        log_entry = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "is_error": error_message is not None,
            **kwargs,
        }

        if error_message:
            log_entry["message"] = error_message
        else:
            log_entry["data"] = data

        st.session_state[self.log_key].append(log_entry)

    def add_searched_period(self, period):
        if "searched_periods" not in st.session_state:
            st.session_state["searched_periods"] = []
        st.session_state["searched_periods"].append(period)

    def add_keywords_report_made(self, keywords):
        if "keywords_report_made" not in st.session_state:
            st.session_state["keywords_report_made"] = []
        st.session_state["keywords_report_made"].append(keywords)

    def get_logs(self):
        return st.session_state.get(self.log_key, [])

    def get_all_keywords(self, search_period=None):
        all_keywords = set()
        for log in self.get_logs():
            if search_period and log.get("search_period") != search_period:
                continue

            if not log.get("is_error") and "data" in log and "results" in log["data"]:
                for item in filter(
                    lambda x: isinstance(x[1]["keywords"], list)
                    and len(x[1]["keywords"]) > 0,
                    log["data"]["results"].items(),
                ):
                    all_keywords.update(item[1]["keywords"])
        return sorted(all_keywords)

    def get_selected_keywords(self):
        """현재 선택된 모든 키워드를 반환합니다."""
        return sorted(
            [
                k.split("_")[2]
                for k, v in st.session_state.items()
                if k.startswith("sk_") and v
            ]
        )

    def is_keyword_selected(self, keyword: str):
        """해당 키워드가 선택되었는지 확인합니다."""
        return st.session_state.get(keyword, False)

    def clear_selected_keywords(self, search_period):
        """선택된 키워드를 모두 제거합니다."""
        for key in list(st.session_state.keys()):
            if key.startswith(f"sk_{search_period}_"):
                del st.session_state[key]

    def get_searched_periods(self):
        return st.session_state.get("searched_periods", [])

    def get_reports(self):
        return list(
            filter(
                lambda x: x.get("type") == "report-make", st.session_state[self.log_key]
            )
        )

    def get_keywords_report_made(self):
        return st.session_state.get("keywords_report_made", [])


class ResponseLogger:
    def show_logs(self, logs):
        """로그 데이터를 표시합니다."""
        if not logs:  # 로그가 없으면 표시하지 않음
            return

        with st.sidebar.expander("Response Logger", expanded=False):
            for log in logs:
                if log.get("is_error"):
                    st.error(log["message"])
                elif log.get("type") == "keyword-search":
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.text(f"[{log['timestamp']}]")
                    with col2:
                        st.text(f"{log['search_period']} Success")
                    st.json(log["data"])
                elif log.get("type") == "report-make":
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.text(f"[{log['timestamp']}]")
                    with col2:
                        st.text(f"{', '.join(log['selected_keywords'])} Success")
                    st.json(log["data"])


class KeywordResultDisplay:
    def show_selected_keywords(self, selected_keywords):
        st.write(", ".join(selected_keywords))

    def show_results(self, search_period: str):
        # 검색 결과 표시
        with st.expander(f"🔍 검색 결과 - {search_period}", expanded=True):
            for keyword in keyword_logs.get_all_keywords(search_period):
                st.checkbox(
                    keyword,
                    value=keyword_logs.is_keyword_selected(
                        f"sk_{search_period}_{keyword}"
                    ),
                    key=f"sk_{search_period}_{keyword}",
                )
            if st.button(
                "키워드 선택 취소", key=f"clear_selected_keywords_{search_period}"
            ):
                keyword_logs.clear_selected_keywords(search_period)
                st.rerun()


class APIManager:
    def __init__(self):
        self.keyword_finder_url = keyword_finder_url
        self.report_maker_url = report_maker_url

    def _is_localhost(self):
        try:
            server_url = st.query_params.get("server", "")
            if not server_url:  # 로컬 개발 서버
                return True

            parsed_url = urlparse(server_url)
            hostname = parsed_url.hostname
            return hostname in ["localhost", "127.0.0.1"] or hostname.startswith(
                "192.168."
            )
        except Exception as e:
            st.error(f"URL 파싱 에러: {str(e)}")
            return False

    async def _get_dummy_data(self):
        dummy_file = Path(__file__).parent / "dummy.json"
        with open(dummy_file, "r", encoding="utf-8") as f:
            dummy_data = json.load(f)
        await asyncio.sleep(1)
        return dummy_data

    async def _get_dummy_report(self):
        dummy_file = Path(__file__).parent / "dummy-report.json"
        with open(dummy_file, "r", encoding="utf-8") as f:
            dummy_data = json.load(f)
        await asyncio.sleep(1)
        return dummy_data

    def search(self, sources, start_date, period_days):
        """
        키워드 검색을 실행하고 결과를 반환합니다.
        """
        if self._is_localhost():
            with st.spinner("데이터를 불러오는 중..."):
                result = asyncio.run(self._get_dummy_data())
            return result
        else:
            try:
                response = requests.post(
                    self.keyword_finder_url,
                    json={
                        "sources": sources,
                        "start_date": start_date,
                        "period_days": period_days,
                    },
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise Exception(f"API 요청 실패: {str(e)}")

    def make_report(
        self,
        sources,
        keywords,
    ):
        if self._is_localhost():
            result = asyncio.run(self._get_dummy_report())
            return result
        else:
            try:
                response = requests.post(
                    self.report_maker_url,
                    json={
                        "sources": sources,
                        "keywords": keywords,
                    },
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise Exception(f"API 요청 실패: {str(e)}")


def main():
    global keyword_logs

    # KeywordLogs 초기화
    keyword_logs = KeywordLogs()

    # 나머지 객체 초기화
    searchlist = SearchSourceList()
    settings = Settings()
    api_manager = APIManager()
    response_logger = ResponseLogger()
    keyword_display = KeywordResultDisplay()

    st.title("해외 건설 동향 리포트 작성")

    with st.sidebar:
        sidebar_top_container = st.sidebar.container()
        sidebar_bottom_container = st.sidebar.container()

        with sidebar_bottom_container:
            with st.sidebar.expander("Settings", expanded=False):
                st.markdown("---")
                st.markdown("### 키워드 검색")
                settings.show_date_settings()
                searchlist.show_checkbox(TaskType.KEYWORD)
                st.markdown("---")
                st.markdown("### 보고서 작성")
                searchlist.show_checkbox(TaskType.REPORT)
                st.markdown("---")

        with sidebar_top_container:
            st.session_state["button_text"] = settings.get_search_button_text()
            button_text = st.session_state["button_text"]
            if st.button(button_text):
                if settings.get_search_period() in keyword_logs.get_searched_periods():
                    st.error("이미 검색한 기간입니다.")
                else:
                    try:
                        # 검색 버튼과 실행
                        selected_sources = searchlist.get_checked_sources(
                            TaskType.KEYWORD
                        )
                        selected_aliases = [source.alias for source in selected_sources]
                        search_params = settings.get_search_params()
                        search_period = settings.get_search_period()

                        start_date = search_params["start_date"]
                        period_days = search_params["period_days"]

                        result = api_manager.search(
                            sources=selected_aliases,
                            start_date=start_date,
                            period_days=period_days,
                        )

                        keyword_logs.add_log(
                            data=result,
                            type="keyword-search",
                            search_period=search_period,
                        )
                        keyword_logs.add_searched_period(search_period)
                    except Exception as e:
                        keyword_logs.add_log(
                            error_message=str(e),
                            type="keyword-search",
                            search_period=search_period,
                        )
                        st.error(str(e))
            selected_keywords = keyword_logs.get_selected_keywords()
            if len(selected_keywords) > 0:
                if st.button("보고서 작성"):
                    if selected_keywords in keyword_logs.get_keywords_report_made():
                        st.error("이미 보고서가 작성되었습니다.")
                    else:
                        with st.spinner("보고서 작성 중..."):
                            sources = searchlist.get_checked_sources(TaskType.REPORT)
                            report_result = api_manager.make_report(
                                sources=sources, keywords=selected_keywords
                            )
                        keyword_logs.add_log(
                            data=report_result,
                            type="report-make",
                            selected_keywords=selected_keywords,
                        )
                        keyword_logs.add_keywords_report_made(selected_keywords)

    # 최신 로그 데이터 확인 및 결과 표시
    searched_periods = keyword_logs.get_searched_periods()
    selected_keywords = keyword_logs.get_selected_keywords()

    col1, col2 = st.columns([3, 1])
    if len(searched_periods) > 0:
        with col2:
            for period in searched_periods:
                keyword_display.show_results(period)

    with col1:
        selected_keywords = keyword_logs.get_selected_keywords()
        keywords_found = keyword_logs.get_all_keywords()
        if len(selected_keywords) > 0:
            st.write("🏷️ 선택된 키워드:")
            keyword_display.show_selected_keywords(selected_keywords)

        elif len(keywords_found) == 0:
            st.write("🏷️ 키워드 검색을 시작해주세요.")
        elif len(keywords_found) > 0:
            st.write("🏷️ 보고서 작성을 위한 키워드를 선택해주세요.")

        reports = keyword_logs.get_reports()
        if len(reports) > 0:
            for report in reports:
                with st.expander(
                    f"{report['data']['keywords']} : {report['data']['report']['title']}",
                    expanded=True,
                ):
                    st.markdown(report["data"]["report"]["texts"])

    with st.sidebar:
        logs = keyword_logs.get_logs()
        if logs:
            response_logger.show_logs(logs)


if __name__ == "__main__":
    main()
