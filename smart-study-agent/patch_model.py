"""Add GROQ_MODEL=qwen/qwen3.8-27b to .env if not already present."""
with open('.env', 'r') as f:
    content = f.read()

if 'GROQ_MODEL' not in content:
    content = content.rstrip() + '\nGROQ_MODEL=qwen/qwen3.8-27b\n'
    with open('.env', 'w') as f:
        f.write(content)
    print('Added GROQ_MODEL to .env')
else:
    # Fix if still set to old wrong value
    import re
    new_content = re.sub(r'GROQ_MODEL\s*=\s*.*', 'GROQ_MODEL=qwen/qwen3.8-27b', content)
    if new_content != content:
        with open('.env', 'w') as f:
            f.write(new_content)
        print('Updated GROQ_MODEL in .env to qwen/qwen3.8-27b')
    else:
        print('GROQ_MODEL already correct in .env')
