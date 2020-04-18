import os
import sys
from flask import Flask, render_template, request, redirect, url_for, session, flash
import requests 
import base64 
import time

import musicclean
import secrets
import classes

app = Flask(__name__)
app.secret_key = "isiokoisi"
SESSION_TYPE = "filesystem"

clean = classes.MusicClean()
user_playlists = classes.Playlists()

debug = True

@app.route("/elements")
def elements():
	return render_template("elements.html")

@app.route("/", methods=["GET", "POST"])
def start():
	if request.method == "GET":
		session["token"] = None
		session["username"] = None

		if debug:
			print("ROUTE: START")
			print("USERNAME (should be None):", session.get("username"))
			print("TOKEN (should be None):", session.get("token"))

		return render_template("home.html", auth_url=musicclean.get_authorize_url())

def is_token_expired(token_info):
    now = int(time.time())
    return token_info["expires_in"] - now < 60

def make_authorization_headers(client_id, client_secret):
	auth_str = client_id + ":" + client_secret
	auth_header = base64.b64encode(auth_str.encode('ascii'))
	return {"Authorization": "Basic %s" % auth_header.decode('ascii')}

def getToken(code):
	payload = {
		"redirect_uri": secrets.REDIRECT_URI,
		"code": code,
		"grant_type": "authorization_code"
	}

	headers = make_authorization_headers(secrets.CLIENT_ID, secrets.CLIENT_SECRET)
	url = "https://accounts.spotify.com/api/token"

	response = requests.post(url, data=payload, headers=headers)
	if response.status_code == 200:
		token_info = response.json()
		token = token_info['access_token']

		session["token"] = token
		session["token_info"] = token_info
	else:
		print("Error retrieving token")

def getPlaylists():
	playlists_dict = musicclean.getPlaylists(session.get("username"), session.get("token"))
	session["playlists_dict"] = playlists_dict
	
	# playlists_list = []
	# for playlist in playlists_dict:
	# 	playlists_list.append(playlist)

	# session["playlists_list"] = playlists_list
	# session["num_playlists"] = len(playlists_list)	
	
	return playlists_dict


@app.route("/playlists/", methods=["GET", "POST"])
def playlists():
	if request.method == "GET":
		if debug:
			print("ROUTE: PLAYLISTS GET")

		playlists_dict = getPlaylists()
			
		return render_template("playlists.html", playlists=playlists_dict, validNum="True")

	if request.method == "POST":
		if debug:
			print("ROUTE: PLAYLISTS POST")

		# playlists_dict = session.get("playlists_dict")

		playlists_dict = getPlaylists()

		playlist_to_clean_id = request.form['select-playlist']
		playlist_to_clean_name = playlists_dict[playlist_to_clean_id]

		session["playlist_to_clean_name"] = playlist_to_clean_name
		session["playlist_to_clean_id"] = playlist_to_clean_id

		clean_playlist_id = musicclean.createPlaylist(session.get("username"), session.get("token"), playlist_to_clean_name)

		# playlists_dict = session.get("playlists_dict")
		_, all_tracks, could_not_clean_tracks = musicclean.getTracks(session.get("username"), session.get("token"), playlist_to_clean_name, playlist_to_clean_id, clean_playlist_id, False)
		session["could_not_clean_tracks"] = could_not_clean_tracks

		clean_tracks = list(set(all_tracks).difference(set(could_not_clean_tracks)))
		session["clean_tracks"] = clean_tracks

		return redirect(url_for('cleanedPlaylist'))

@app.route("/cleanedplaylist/", methods=["GET"])
def cleanedPlaylist():
	playlist_to_clean_name = session.get("playlist_to_clean_name")
	clean_tracks = session.get("clean_tracks")
	could_not_clean_tracks = session.get("could_not_clean_tracks")

	has_uncleaned_tracks = "False"
	if len(could_not_clean_tracks) > 0:
		has_uncleaned_tracks = "True"

	return render_template("cleaned_playlist.html", playlistName=playlist_to_clean_name,  cleanTracks=clean_tracks, notCleanTracks=could_not_clean_tracks, hasNotClean = has_uncleaned_tracks)


def getUsername():
	headers = {
		"Authorization": "Bearer " + session.get("token"),
	}

	url = "https://api.spotify.com/v1/me"

	response = requests.get(url, headers=headers)
	if response.status_code == 200:
		user = response.json()
		session["username"] = user["id"]
	else:
		print("Error retrieving username")

@app.route("/callback/", methods=["GET"])
def callback():
	if debug:
		print("ROUTE: CALLBACK")

	getToken(request.args['code'])

	if debug:
		print("Got new token:", session.get("token"))

	getUsername()

	if debug:
		print("Got username:", session.get("username"))

	return redirect(url_for('playlists'))

if __name__ == '__main__':
	app.run(debug=True)