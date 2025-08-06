import requests
from bs4 import BeautifulSoup

def get_stock_current_price(stock_code: str) -> float:
    """
    네이버 금융에서 특정 종목(예: '005930')의 현재가를 반환합니다.
    
    :param stock_code: 종목코드 (예: '005930'은 삼성전자)
    :return: 현재가 (실수형), 가져오지 못할 경우 None
    """
    # 네이버 금융 종목 페이지 URL 구성
    url = f"https://finance.naver.com/item/main.nhn?code={stock_code}"
    
    try:
        response = requests.get(url)
        # 네이버는 euc-kr 인코딩을 사용합니다.
        response.encoding = "euc-kr"
    except Exception as e:
        print("HTTP 요청 실패:", e)
        return None

    # BeautifulSoup으로 HTML 파싱
    soup = BeautifulSoup(response.text, "html.parser")
    
    # 오늘의 가격 정보가 포함된 div (class "today")
    today_div = soup.find("div", class_="today")
    if not today_div:
        print("오늘의 가격 정보를 찾지 못했습니다.")
        return None
    
    # 현재가는 "span" 태그 내 class "blind"에 담겨있는 경우가 많습니다.
    price_span = today_div.find("span", class_="blind")
    if not price_span:
        print("현재가 정보를 찾지 못했습니다.")
        return None

    # 쉼표(,) 제거 후 실수형 변환
    price_text = price_span.text.replace(",", "").strip()
    try:
        current_price = float(price_text)
        return current_price
    except Exception as e:
        print("가격 파싱 실패:", e)
        return None

# 사용 예시
if __name__ == "__main__":
    stock_code = "005930"  # 삼성전자 예시
    price = get_stock_current_price(stock_code)
    if price is not None:
        print(f"{stock_code} 종목의 현재가: {price}")
    else:
        print("현재가를 가져오지 못했습니다.")
