from flask import Flask

app = Flask(__name__)

@app.route("/")
def home():
    return "Hello depuis Flask sur Vercel !"

# Pour que Vercel détecte automatiquement app en tant que handler WSGI,
# il suffit d’avoir l’objet `app` au niveau global.
if __name__ == "__main__":
    app.run()
