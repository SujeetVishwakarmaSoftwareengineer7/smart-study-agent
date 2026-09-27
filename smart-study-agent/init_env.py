import shutil, os
if not os.path.exists('.env') or os.path.getsize('.env') == 0:
    shutil.copy('.env.example', '.env')
    print('Copied .env.example -> .env')
else:
    print('.env already has content, skipping copy')
