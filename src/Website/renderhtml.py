from string import Template

import codecs

PATH_TO_TEMPLATE = "template.html"
TEMPLATE = Template(open(PATH_TO_TEMPLATE).read())

PAGES = [('Emission Calculator', 'index.part', 'index.html'),
         ('About Us', 'about.part', 'about.html'),
         ('Alternatives', 'alternatives.part', 'alternatives.html'),
         ('Feedback', 'feedback.part', 'feedback.html'),
        # ... etc ...
         ]
         
def main():
    for t, source, dest in PAGES:
        if source != 'index.part':
            body = open(source).read()
            html = TEMPLATE.substitute(title=t, content=body)
            with codecs.open(dest, 'w', 'utf-8') as f:
                f.write(html)
        else:
            index_temp = Template(open(source).read())
            f = open("weather.csv", "r")
            st = f.read()
            parts = st.split(",")
            body = index_temp.substitute(icon=parts[3], forecast=parts[2], cel=parts[1], far=parts[0], game=parts[4])
            html = TEMPLATE.substitute(title=t, content=str(body))
            with codecs.open(dest, 'w', 'utf-8') as f:
                f.write(html)
            
if __name__ == "__main__":
    main()
