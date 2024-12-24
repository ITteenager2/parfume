import asyncio
from openai import OpenAI
from config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY)

async def generate_recommendation(user_data, user_message=""):
    prompt = f"""
    Пользователь:
    Возраст: {user_data.get('age')}
    Пол: {user_data.get('gender')}
    Предпочитаемые ароматы: {user_data.get('preferred_fragrances')}
    Местоположение: {user_data.get('location')}

    История покупок: {user_data.get('order_history', 'Нет данных')}

    Запрос пользователя: {user_message}

    На основе этой информации, пожалуйста, предоставьте персонализированную рекомендацию по парфюмерии.
    Учтите сезонность, текущие акции и специальные предложения.
    """

    loop = asyncio.get_event_loop()
    try:
        response = await loop.run_in_executor(None, lambda: client.completions.create(
            model="gpt-3.5-turbo-instruct",  # Using a valid model
            prompt=prompt,
            max_tokens=200
        ))
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"Error in generate_recommendation: {str(e)}")
        return "Извините, произошла ошибка при генерации рекомендации. Пожалуйста, попробуйте еще раз позже."

