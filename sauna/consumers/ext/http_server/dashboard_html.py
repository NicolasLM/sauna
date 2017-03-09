dashboard_html = """<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Sauna status</title>
<style>
body {{
    background-color: rgba(114, 254, 149, 0.38);
}}
h1   {{color: blue;}}
.content {{
    border-radius: 25px;
    border: 1px solid black;
    background-color: white;
    width: 80%;
    margin-left: auto;
    margin-right: auto;
}}
.st {{
    padding: 5px 10px 5px 10px;
}}
.st_0 {{
    background-color: rgba(166, 241, 166, 0.54);
    border-radius: 25px;
}}
.st_1 {{
    background-color: rgba(249, 215, 46, 0.54);
    border-radius: 25px;
}}
.st_2 {{
    background-color: rgba(249, 93, 46, 0.54);
    border-radius: 25px;
}}
.st_3 {{
    background-color: rgba(45, 149, 222, 0.54);
    border-radius: 25px;
}}
table caption {{
    font-size: 50px;
}}
table {{
    width: 80%;
    border-collapse: collapse;
    margin-left: auto;
    margin-right: auto;
}}
th, td {{
    padding: 15px;
    text-align: left;
    border-top:1pt solid black;
}}
</style>
</head>
<body>
<div class="content">
<table>
<caption>Sauna status</caption>
{}
</table>
</div>
</body>
</html>"""
