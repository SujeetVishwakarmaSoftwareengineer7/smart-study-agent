from dotenv import dotenv_values
d = dotenv_values('.env')
for k in d:
    v = d[k] or ''
    is_placeholder = v in ('your_groq_api_key_here', 'change-this-to-a-random-secret-key', '')
    status = '[NOT SET / PLACEHOLDER]' if is_placeholder else '[SET]'
    print(f'{k} = {status}')
