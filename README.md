# SmartBite Restaurant Chatbot

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Run `pip install -r requirements.txt`.
4. Run `streamlit run app.py`.

## Deploy to Streamlit Community Cloud
1. Upload `app.py`, `requirements.txt`, and `restaurant_menu(3).csv` to a GitHub repository.
2. Go to https://share.streamlit.io/ and sign in.
3. Select **Create app**, choose your repository and `app.py`.
4. Click **Deploy**.

## Food images (optional)
Create an `images` folder. Put image files in it using a normalized dish name, for example:
- `butter_chicken.jpg`
- `veg_burger.jpg` (only if the dish name normalizes to `veg_burger`)
- `chicken_noodles.jpg`

The app automatically looks for an image named after the dish, in `.jpg`, `.jpeg`, `.png`, or `.webp` format. Images are optional.
