import gspread
from oauth2client.service_account import ServiceAccountCredentials
from typing import Dict, Any
from config import GOOGLE_SHEETS_CREDENTIALS, GOOGLE_SHEETS_ID

def update_google_sheets(data: Dict[str, Any]):
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_SHEETS_CREDENTIALS, scope)
    client = gspread.authorize(creds)

    sheet = client.open_by_key(GOOGLE_SHEETS_ID).sheet1
    
    # Обновляем данные в Google Sheets
    sheet.update('A1', [['Метрика', 'Значение']])
    sheet.update('A2', [['Средняя оценка', data['average_score']]])
    sheet.update('A3', [['Всего отзывов', data['total_feedback']]])

