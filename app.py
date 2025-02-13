import streamlit as st
from enum import Enum
import json
import asyncio
from pathlib import Path
import requests
import re
import datetime
from streamlit_local_storage import LocalStorage


keyword_finder_url = st.secrets["keyword-finder-url"]
report_maker_url = st.secrets["report-maker-url"]
db_handler_url = st.secrets["db-handler-url"]
app_manager_url = st.secrets["app-manager-url"]

user_id = None
keyword_logs = None
db_handler = None


class SearchKeywordType(Enum):
    MANUAL = "manual"
    AUTO = "auto"


class TaskType(Enum):
    KEYWORD = "keyword"
    REPORT = "report"


class SettingsType(Enum):
    AUTO_CRON = "auto-cron"
    AUTO_KEYWORD = "auto-keyword"
    AUTO_REPORT = "auto-report"
    KEYWORD = "keyword"
    REPORT = "report"


class SearchSourceList:
    def __init__(self, sources=None):
        self.sources = sources or []

    def show_checkbox(self, task_type: TaskType):
        """소스별 체크박스를 표시합니다."""
        for source in self.sources:
            checkbox_key = f"{task_type.value}_checkbox_{source['Alias']}"
            st.checkbox(
                source["Name"], value=True, key=checkbox_key, help=source["Url"]
            )

    def get_checked_sources(self, task_type: TaskType):
        """체크된 소스의 alias 목록을 반환합니다."""
        return [
            source["Alias"]
            for source in self.sources
            if st.session_state.get(
                f"{task_type.value}_checkbox_{source['Alias']}", False
            )
        ]


class DisplayManager:
    def show_settings(self, setting, settings_type: SettingsType):
        if settings_type == SettingsType.AUTO_CRON:
            st.toggle(
                setting["autoDaily"]["executionStatusLabel"],
                value=setting["autoDaily"]["executionStatus"],
                key=setting["autoDaily"]["executionStatusKey"],
                on_change=lambda: DBHandler().update_setting(
                    user_id=setting["userId"],
                    key=setting["autoDaily"]["executionStatusKey"],
                    value={
                        "autoDaily": {
                            "executionStatus": not setting["autoDaily"][
                                "executionStatus"
                            ]
                        }
                    },
                ),
            )

            if setting["autoDaily"]["executionStatus"]:
                st.text_input(
                    setting["autoDaily"]["executionTimeLabel"],
                    value=setting["autoDaily"]["executionTime"],
                    key=setting["autoDaily"]["executionTimeKey"],
                    disabled=True,  # 비활성화
                )
            else:
                st.time_input(
                    setting["autoDaily"]["executionTimeLabel"],
                    value=datetime.datetime.strptime(
                        setting["autoDaily"]["executionTime"], "%H:%M"
                    ),
                    key=setting["autoDaily"]["executionTimeKey"],
                    on_change=lambda: DBHandler().update_setting(
                        user_id=setting["userId"],
                        key=setting["autoDaily"]["executionTimeKey"],
                        value={
                            "autoDaily": {
                                "executionTime": st.session_state.get(
                                    setting["autoDaily"]["executionTimeKey"]
                                ).strftime("%H:%M")
                            }
                        },
                    ),
                )

        elif settings_type == SettingsType.KEYWORD:
            setting["dateOptionMap"] = dict(
                sorted(setting["dateOptionMap"].items(), key=lambda item: item[1])
            )

            st.date_input(
                setting["dateSelectLabel"],
                key=setting["dateSelectKey"],
            )

            st.selectbox(
                setting["dateOptionLabel"],
                options=setting["dateOptionMap"].keys(),
                key=setting["dateOptionKey"],
            )

        for source in setting.get("sources", []):

            def on_change_callback(source=source):
                DBHandler().update_setting(
                    user_id=setting["userId"],
                    key=source["checkboxKey"],
                    value={
                        "sources": [
                            {
                                "checkboxKey": source["checkboxKey"],
                                "isSelect": not source["isSelect"],
                            }
                        ]
                    },
                )

            if source["groupId"]:
                st.write(source["groupId"])
            st.checkbox(
                source["name"],
                value=source["isSelect"],
                key=source["checkboxKey"],
                help=source["url"],
                on_change=on_change_callback,
            )

        # for sourceGroup in setting.get("sourceGroups", []):
        #     st.json(sourceGroup)
        #     st.write(sourceGroup["name"])

        #     for source in sourceGroup["sources"]:

        #         def on_change_callback(source=source):
        #             DBHandler().update_setting(
        #                 user_id=setting["userId"],
        #                 key=source["checkboxKey"],
        #                 value={
        #                     "sourceGroups": [
        #                         {
        #                             "index": sourceGroup["index"],
        #                             "sources": [
        #                                 {
        #                                     "index": source["index"],
        #                                     "checkboxKey": source["checkboxKey"],
        #                                     "isSelect": not source["isSelect"],
        #                                 }
        #                             ],
        #                         }
        #                     ]
        #                 },
        #             )

        #         st.checkbox(
        #             # source["name"],
        #             "?",
        #             value=source["isSelect"],
        #             key=source["checkboxKey"],
        #             help=source["url"],
        #             on_change=on_change_callback,
        #         )

    def show_keywords(self, keywords):
        # st.json(keywords)
        date = st.expander(keywords["date"], expanded=True)
        if len(keywords["data"]) > 0:
            with date:
                for keyword in keywords["data"]:
                    st.checkbox(
                        keyword["keyword"],
                        value=False,
                        key=keyword[
                            "checkboxKey"
                        ],  # VIEW#DATE#2025-01-23#KEYWORD#artificial_intelligence_in_construction
                    )

    def show_keywords_searched(self, keywords_keyword, keywords_document):
        tab1, tab2 = st.tabs(["Keyword", "News"])

        with tab1:
            for date, keyword in list(keywords_keyword.items())[::-1]:
                date_expander = st.expander(date, expanded=False)
                with date_expander:
                    for keyword in keyword:
                        st.checkbox(
                            keyword["keyword"]["viewLabel"],
                            value=False,
                            key=keyword["keyword"]["viewCheckboxKey"],
                        )
                        for document in keyword["documents"]:
                            st.markdown(
                                "<p style='font-size:14px;margin-left:18px;'>\n"
                                f"<a style='text-decoration: none; \n"
                                "color: inherit;' \n"
                                f"href='{document['url']}' target='_blank'>{document['titleShort']}</a>\n"
                                "</p>",
                                unsafe_allow_html=True,
                            )
        with tab2:
            for date, document in list(keywords_document.items())[::-1]:
                date_expander = st.expander(date, expanded=False)
                with date_expander:
                    for document in document:
                        st.markdown(
                            "<p style='font-size:20px;margin-left:-4px;'>\n"
                            f"<a style='text-decoration: none; \n"
                            "color: inherit;' \n"
                            f"href='{document['url']}' target='_blank'>{document['titleShort']}</a>\n"
                            "</p>",
                            unsafe_allow_html=True,
                        )
                        for keyword in document["keywords"]:
                            st.checkbox(
                                keyword["viewLabel"],
                                value=False,
                                key=keyword["viewCheckboxKey"],
                            )

    def show_selected_keywords(self):
        st.session_state["selected_keywords"] = []


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
        selected_period = st.session_state.get(self.period_key)

        # 숫자만 추출
        period_days = int(re.search(r"\d+", selected_period)[0])

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
    def __init__(self, user_settings=None, app_config=None):
        self.log_key = "response_logs"
        self.settings_key = "user_settings"
        self.app_config = app_config["data"]
        # 세션 스테이트 초기화
        if self.log_key not in st.session_state:
            st.session_state[self.log_key] = []

        # 사용자 설정 저장
        if user_settings:
            st.session_state[self.settings_key] = user_settings["data"]["viewSettings"]

    def get_app_title(self):
        return self.app_config["title"]

    def get_settings(self):
        """설정 목록을 반환합니다."""
        return st.session_state.get(self.settings_key, [])

    def get_setting(self, settings_type: SettingsType):
        """설정 정보를 반환합니다."""
        return next(
            (
                item
                for item in self.get_settings()
                if item["settingType"] == settings_type.value
            ),
            None,
        )

    def get_date_select_and_option(self):
        keyword_setting = self.get_setting(SettingsType.KEYWORD)
        date_option_key = keyword_setting["dateOptionKey"]
        date_select_key = keyword_setting["dateSelectKey"]
        return (
            st.session_state.get(date_select_key, ""),
            keyword_setting["dateOptionMap"][st.session_state.get(date_option_key, "")],
        )

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
        selected = []
        for key, value in st.session_state.items():
            if key.startswith("VIEW#DATE#") and "#KEYWORD#" in key and value:
                # VIEW#DATE#2025-01-23#KEYWORD#artificial_intelligence_in_construction 형식에서
                # artificial_intelligence_in_construction 부분만 추출
                keyword = key.split("#KEYWORD#")[1]
                selected.append(keyword)
        return sorted(selected)

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
                    # st.json(log["data"])
                elif log.get("type") == "report-make":
                    col1, col2 = st.columns([1, 1])
                    with col1:
                        st.text(f"[{log['timestamp']}]")
                    with col2:
                        st.text(f"{', '.join(log['selected_keywords'])} Success")
                    # st.json(log["data"])


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
        self.app_manager_url = app_manager_url

    def _is_localhost(self):
        is_local = st.query_params.get("localhost", "")
        return bool(is_local)

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

    def search(
        self,
        search_keyword_type: SearchKeywordType,
        start_date,
        period_days,
    ):
        """
        키워드 검색을 실행하고 결과를 반환합니다.
        """
        try:
            response = requests.post(
                f"{self.app_manager_url}/searchKeyword",
                json={
                    "user_id": user_id,
                    "search_keyword_type": search_keyword_type.value,
                    "start_date": start_date,
                    "period_days": period_days,
                },
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"API 요청 실패: {str(e)}")

    def make_report(self, keywords, search_keyword_type: SearchKeywordType):
        if self._is_localhost():
            result = asyncio.run(self._get_dummy_report())
            return result
        else:
            try:
                response = requests.post(
                    f"{self.app_manager_url}/makeReport",
                    json={
                        "user_id": user_id,
                        "search_keyword_type": search_keyword_type.value,
                        "keywords": keywords,
                    },
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise Exception(f"API 요청 실패: {str(e)}")

    def make_report_new(self, keywords, documents):
        if self._is_localhost():
            result = asyncio.run(self._get_dummy_report())
            return result
        else:
            try:
                response = requests.post(
                    f"{self.app_manager_url}/makeReportNew",
                    json={
                        "user_id": user_id,
                        "keywords": keywords,
                        "news": documents,
                    },
                )
                response.raise_for_status()
                return response.json()
            except Exception as e:
                raise Exception(f"API 요청 실패: {str(e)}")


class DBHandler:
    def __init__(self):
        self.base_url = st.secrets["db-handler-url"]

    def create_user_if_needed(self):
        """Query 파라미터의 user 값을 확인하여 필요한 경우 사용자를 생성합니다."""
        try:
            if user_id and user_id.isdigit():
                response = requests.post(
                    f"{self.base_url}/createUser", json={"user_id": int(user_id)}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            st.error(f"사용자 생성 실패: {str(e)}")
            return None

    def get_settings(self):
        """사용자 설정과 소스 정보를 가져옵니다."""
        try:
            if user_id and user_id.isdigit():
                response = requests.get(
                    f"{self.base_url}/getSettings",
                    params={"user_id": int(user_id)},
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            st.error(f"사용자 조회 실패: {str(e)}")
            return None

    def update_setting(
        self,
        user_id: str,
        key: str,
        value,
    ):

        try:
            requests.put(
                f"{self.base_url}updateSetting",
                json={
                    "user_id": user_id,
                    "setting_key": key,
                    "value": value,
                },
            )
        except Exception as e:
            st.error(f"사용자 설정 업데이트 실패: {str(e)}")

    def get_app_config(self):
        response = requests.get(f"{self.base_url}/getAppConfig")
        response.raise_for_status()
        return response.json()

    def get_keywords_by_date(self, date):
        response = requests.get(
            f"{self.base_url}/getKeywords",
            params={"date": date},
        )
        response.raise_for_status()
        return response.json()

    def get_keywords_searched(self):
        response = requests.get(
            f"{self.base_url}/getKeywordsSearched",
        )
        response.raise_for_status()
        return response.json()


def main():
    global keyword_logs, db_handler, user_id
    localS = LocalStorage()

    # user 값을 query parameter 또는 localStorage에서 가져오기
    query_user = st.query_params.get("user")
    # stored_user = localS.getItem("user")

    # user 값이 없고 localStorage에도 없는 경우
    # if not query_user and not stored_user:
    #     # 새 사용자 생성
    #     result = db_handler.create_user_if_needed()
    #     if result and "user_id" in result:
    #         new_user_id = str(result["user_id"])

    # # query parameter에는 있지만 localStorage에는 없는 경우
    # elif query_user and not stored_user:
    #     localS.setItem("user", "query_user")

    user_id = query_user if query_user else "1038"
    # st.write(user_id)
    # DB 핸들러 초기화 및 사용자 설정 가져오기
    db_handler = DBHandler()
    user_settings = db_handler.get_settings()
    app_config = db_handler.get_app_config()
    # KeywordLogs 초기화 (사용자 설정 전달)
    keyword_logs = KeywordLogs(user_settings, app_config)

    # Settings 초기화
    settings = Settings()

    # 나머지 객체 초기화
    sources = user_settings.get("sources", []) if user_settings else []
    searchlist = SearchSourceList(sources)
    api_manager = APIManager()
    response_logger = ResponseLogger()
    keyword_display = KeywordResultDisplay()
    display_manager = DisplayManager()

    st.title(keyword_logs.get_app_title())
    # 페이지 로드 시 사용자 생성 확인
    # db_handler.create_user_if_needed()
    # st.json(db_handler.get_settings())

    with st.sidebar:
        sidebar_top_container = st.sidebar.container()
        sidebar_bottom_container = st.sidebar.container()

        with sidebar_bottom_container:
            with st.sidebar.expander("Settings", expanded=False):
                tab1, tab3 = st.tabs(["매일 키워드", "키워드 수동 검색"])
                with tab1:
                    auto_cron_setting = keyword_logs.get_setting(SettingsType.AUTO_CRON)
                    if auto_cron_setting:
                        display_manager.show_settings(
                            auto_cron_setting, SettingsType.AUTO_CRON
                        )
                    auto_keyword_setting = keyword_logs.get_setting(
                        SettingsType.AUTO_KEYWORD
                    )
                    if auto_keyword_setting:
                        display_manager.show_settings(
                            auto_keyword_setting, SettingsType.AUTO_KEYWORD
                        )
                with tab3:
                    keyword_setting = keyword_logs.get_setting(SettingsType.KEYWORD)
                    if keyword_setting:
                        display_manager.show_settings(
                            keyword_setting, SettingsType.KEYWORD
                        )

        with sidebar_top_container:
            st.session_state["button_text"] = settings.get_search_button_text()
            button_text = st.session_state["button_text"]
            if st.button(button_text):
                if settings.get_search_period() in keyword_logs.get_searched_periods():
                    st.error("이미 검색한 기간입니다.")
                else:
                    # search_params = settings.get_search_params()
                    search_period = settings.get_search_period()
                    try:
                        # 검색 버튼과 실행
                        selected_sources = searchlist.get_checked_sources(
                            TaskType.KEYWORD
                        )
                        selected_aliases = [source for source in selected_sources]
                        # hi = keyword_logs.get_date_select_and_option()
                        # st.write(hi)
                        start_date, period_days = (
                            keyword_logs.get_date_select_and_option()
                        )

                        result = api_manager.search(
                            SearchKeywordType.MANUAL,
                            start_date=start_date.strftime("%Y-%m-%d"),
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
                    report_result = api_manager.make_report(
                        keywords=selected_keywords,
                        search_keyword_type=SearchKeywordType.MANUAL,
                    )
                    # st.json(report_result)
                    keyword_logs.add_log(
                        data=report_result,
                        type="report-make",
                        selected_keywords=selected_keywords,
                    )

    # 최신 로그 데이터 확인 및 결과 표시
    searched_periods = keyword_logs.get_searched_periods()
    selected_keywords = keyword_logs.get_selected_keywords()

    def remove_duplicates(data):
        """리스트에서 중복된 딕셔너리를 제거하는 함수"""
        unique_data = []
        for item in data:
            if item not in unique_data:
                unique_data.append(item)
        return unique_data

    col1, col2 = st.columns([3, 5])
    report_response = None
    with col1:

        col1_top_container = st.container()
        col1_bottom_container = st.container()
        keywords_searched = db_handler.get_keywords_searched()
        selected_keywords = remove_duplicates(
            [
                *[
                    item["keyword"]
                    for item in [
                        v
                        for k, v in keywords_searched["data"]["viewKeyMap"][
                            "keywordKeyMap"
                        ].items()
                        if st.session_state.get(k, False)
                    ]
                ],
                *[
                    item["keyword"]
                    for item in [
                        v
                        for k, v in keywords_searched["data"]["viewKeyMap"][
                            "documentKeyMap"
                        ].items()
                        if st.session_state.get(k, False)
                    ]
                ],
            ]
        )
        selected_news = remove_duplicates(
            [
                *[
                    page
                    for item in [
                        v
                        for k, v in keywords_searched["data"]["viewKeyMap"][
                            "keywordKeyMap"
                        ].items()
                        if st.session_state.get(k, False)
                    ]
                    for page in item["documents"]
                ],
                *[
                    item["document"]
                    for item in [
                        v
                        for k, v in keywords_searched["data"]["viewKeyMap"][
                            "documentKeyMap"
                        ].items()
                        if st.session_state.get(k, False)
                    ]
                ],
            ]
        )
        with col1_top_container:
            report_button = st.button("보고서 작성", key="report_button")
            if report_button and len(selected_keywords) > 0:
                st.write("보고서 작성 중...")
                report_response = api_manager.make_report_new(
                    selected_keywords,
                    selected_news,
                )
            else:
                st.write("키워드를 선택해주세요.")

            st.write("🏷️ 선택된 키워드:")
            for keyword in selected_keywords:
                st.markdown(
                    "<p style='font-size:16px;margin-left:18px;'>\n"
                    f"{keyword['ko']}\n"
                    "</p>",
                    unsafe_allow_html=True,
                )
            st.write("🏷️ 선택된 뉴스:")
            for news in selected_news:
                st.markdown(
                    "<p style='font-size:16px;margin-left:18px;'>\n"
                    f"<a style='text-decoration: none; \n"
                    "color: inherit;' \n"
                    f"href='{news['url']}' target='_blank'>{news['titleShort']}</a>\n"
                    "</p>",
                    unsafe_allow_html=True,
                )
            st.divider()
        with col1_bottom_container:
            st.write("날짜별 키워드")

            display_manager.show_keywords_searched(
                keywords_searched["data"]["keywords"],
                keywords_searched["data"]["documents"],
            )

    with col2:

        if report_response:
            st.markdown(report_response["data"])

    with st.sidebar:
        logs = keyword_logs.get_logs()
        if logs:
            response_logger.show_logs(logs)


if __name__ == "__main__":
    main()
