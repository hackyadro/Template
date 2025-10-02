FROM nginx:alpine

# Создаем простую HTML заглушку
RUN echo '<!DOCTYPE html>\n\
<html lang="ru">\n\
<head>\n\
    <meta charset="UTF-8">\n\
    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n\
    <title>Indoor Navigation - Frontend</title>\n\
    <style>\n\
        * {\n\
            margin: 0;\n\
            padding: 0;\n\
            box-sizing: border-box;\n\
        }\n\
        body {\n\
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;\n\
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);\n\
            display: flex;\n\
            justify-content: center;\n\
            align-items: center;\n\
            min-height: 100vh;\n\
            color: #333;\n\
        }\n\
        .container {\n\
            background: white;\n\
            border-radius: 20px;\n\
            padding: 3rem;\n\
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);\n\
            max-width: 600px;\n\
            text-align: center;\n\
        }\n\
        h1 {\n\
            color: #667eea;\n\
            margin-bottom: 1rem;\n\
            font-size: 2.5rem;\n\
        }\n\
        .status {\n\
            display: inline-block;\n\
            background: #10b981;\n\
            color: white;\n\
            padding: 0.5rem 1rem;\n\
            border-radius: 50px;\n\
            margin: 1rem 0;\n\
            font-weight: bold;\n\
        }\n\
        .info {\n\
            margin: 2rem 0;\n\
            text-align: left;\n\
            background: #f3f4f6;\n\
            padding: 1.5rem;\n\
            border-radius: 10px;\n\
        }\n\
        .info h3 {\n\
            color: #667eea;\n\
            margin-bottom: 1rem;\n\
        }\n\
        .info ul {\n\
            list-style: none;\n\
            padding-left: 0;\n\
        }\n\
        .info li {\n\
            padding: 0.5rem 0;\n\
            border-bottom: 1px solid #e5e7eb;\n\
        }\n\
        .info li:last-child {\n\
            border-bottom: none;\n\
        }\n\
        .info a {\n\
            color: #667eea;\n\
            text-decoration: none;\n\
            font-weight: 500;\n\
        }\n\
        .info a:hover {\n\
            text-decoration: underline;\n\
        }\n\
        .emoji {\n\
            font-size: 4rem;\n\
            margin-bottom: 1rem;\n\
        }\n\
        code {\n\
            background: #1f2937;\n\
            color: #10b981;\n\
            padding: 0.2rem 0.5rem;\n\
            border-radius: 4px;\n\
            font-family: "Courier New", monospace;\n\
        }\n\
    </style>\n\
</head>\n\
<body>\n\
    <div class="container">\n\
        <div class="emoji">📍</div>\n\
        <h1>Indoor Navigation</h1>\n\
        <div class="status">Frontend Placeholder</div>\n\
        \n\
        <div class="info">\n\
            <h3>🔌 Backend API доступен:</h3>\n\
            <ul>\n\
                <li><strong>API:</strong> <a href="http://localhost:8000" target="_blank">http://localhost:8000</a></li>\n\
                <li><strong>Swagger:</strong> <a href="http://localhost:8000/docs" target="_blank">http://localhost:8000/docs</a></li>\n\
                <li><strong>ReDoc:</strong> <a href="http://localhost:8000/redoc" target="_blank">http://localhost:8000/redoc</a></li>\n\
            </ul>\n\
        </div>\n\
\n\
        <div class="info">\n\
            <h3>🚀 Быстрый тест API:</h3>\n\
            <ul>\n\
                <li><code>GET /health</code> - проверка работы</li>\n\
                <li><code>GET /beacons</code> - список маяков</li>\n\
                <li><code>POST /positions/calculate</code> - вычислить позицию</li>\n\
            </ul>\n\
        </div>\n\
\n\
        <p style="margin-top: 2rem; color: #6b7280; font-size: 0.9rem;">\n\
            Frontend в разработке. Используйте Swagger UI для тестирования API.\n\
        </p>\n\
    </div>\n\
</body>\n\
</html>' > /usr/share/nginx/html/index.html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
