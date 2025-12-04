// REPLACE THIS URL with your API Gateway URL!
const API_URL = 'https://az4y9bink2.execute-api.us-east-1.amazonaws.com/prod/content';

let currentUser = null;
let currentUserId = null;
let currentMovieId = null;
let isAuthenticated = false;

const movieDescriptions = {
    "movie1": "The Bird Movie is a heartwarming story about a bird perched on a tree branch, singing melodious tunes.",
    "movie2": "Windmill Watch shows the serene beauty of windmills in a picturesque countryside setting, beautiful colors of the setting sun.",
    "movie3": "Chill City is a relaxing journey through a city showing the movement as people go about their daily lives, with calming background music."
};

const movieTitles = {
    "movie1": "The Bird Movie",
    "movie2": "Windmill Watch",
    "movie3": "Chill City"
};

//-------------------------------- USER AUTHENTICATION -------------------------------
async function login() {
    console.log('Login function called'); // Debug
    
    const usernameInput = document.getElementById('username');
    const accessKeyInput = document.getElementById('accessKey');
    
    console.log('Username input:', usernameInput); // Debug
    console.log('AccessKey input:', accessKeyInput); // Debug
    
    if (!usernameInput || !accessKeyInput) {
        alert('Error: Cannot find input fields');
        return;
    }
    
    const username = usernameInput.value;
    const accessKey = accessKeyInput.value;
    
    console.log('Username:', username); // Debug
    console.log('AccessKey:', accessKey); // Debug
    
    if (!username || !accessKey) {
        alert('Please enter both IAM Username and Access Key');
        return;
    }
    
    // Show loading state
    const loginBtn = document.querySelector('.login-section button');
    const originalText = loginBtn.textContent;
    loginBtn.textContent = 'Authenticating...';
    loginBtn.disabled = true;
    
    try {
        console.log('Sending request to:', API_URL); // Debug
        
        // Call Lambda function to authenticate user
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: 'authenticate',
                username: username,
                accessKey: accessKey
            })
        });
        
        console.log('Response status:', response.status); // Debug
        
        const result = await response.json();
        console.log('Result:', result); // Debug
        
        const data = result.body ? JSON.parse(result.body) : result;
        console.log('Parsed data:', data); // Debug
        
        if (data.authenticated) {
            // Authentication successful
            isAuthenticated = true;
            currentUser = data.username;
            currentUserId = data.userId;
            
            document.getElementById('userDisplay').textContent = currentUser;
            document.getElementById('loginSection').style.display = 'none';
            document.getElementById('moviesSection').style.display = 'block';
            document.getElementById('userMoviesSection').style.display = 'block';
            
            loadAllProgress();
            getUserMovies();
        } else {
            // Authentication failed
            alert('Authentication Failed: ' + (data.error || 'Invalid credentials or insufficient privileges'));
            loginBtn.textContent = originalText;
            loginBtn.disabled = false;
        }
    } catch (error) {
        alert('Authentication Error: ' + error.message);
        console.error('Authentication error:', error);
        loginBtn.textContent = originalText;
        loginBtn.disabled = false;
    }
}



//-------------------------------- MOVIE PROGRESS TRACKING -------------------------------
async function loadAllProgress() {
    if (!isAuthenticated) {
        alert('Please login first');
        return;
    }
    
    const movies = ['movie1', 'movie2', 'movie3'];
    
    for (const movieId of movies) {
        try {
            const response = await fetch(API_URL, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    action: 'getProgress',
                    userId: currentUserId,
                    movieId: movieId
                })
            });
            
            const result = await response.json();
            const data = result.body ? JSON.parse(result.body) : result;
            const progress = data.watchProgress || 0;
            document.getElementById(`progress-${movieId}`).style.width = progress + '%';
        } catch (error) {
            console.error(`Error loading progress for ${movieId}:`, error);
        }
    }
}


//-------------------------------- PLAYING MOVIE -------------------------------
async function playMovie(movieId) {
    if (!isAuthenticated) {
        alert('Please login first');
        return;
    }
    
    currentMovieId = movieId;
    
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: 'getVideo',
                movieId: movieId
            })
        });
        
        const result = await response.json();
        const data = result.body ? JSON.parse(result.body) : result;
        
        if (data.videoUrl) {
            document.getElementById('moviesSection').style.display = 'none';
            document.getElementById('userMoviesSection').style.display = 'none'; 
            document.getElementById('playerSection').style.display = 'block';
            document.getElementById('currentMovie').textContent = `Now Playing: ${movieTitles[movieId]}`;
            
            const videoPlayer = document.getElementById('videoPlayer');
            videoPlayer.src = data.videoUrl;
            videoPlayer.play();

            // Set description and show TTS button
            const descText = document.getElementById('descriptionText');
            const ttsButton = document.getElementById('ttsButton');

            if (movieDescriptions[movieId]) {
                descText.textContent = movieDescriptions[movieId];
                ttsButton.style.display = 'inline-block';
            } else {
                descText.textContent = '';
                ttsButton.style.display = 'none';
            }
        }
    } catch (error) {
        alert('Error loading video: ' + error.message);
        console.error(error);
    }
}

// For text-to-speech (AWS Polly integration placeholder)
function playTextToSpeech() {
    if (!currentMovieId || !movieDescriptions[currentMovieId]) return;

    const text = movieDescriptions[currentMovieId];
    
    // Here you can integrate AWS Polly API to play the TTS audio
    // For now, we can use the Web Speech API as a placeholder
    const utterance = new SpeechSynthesisUtterance(text);
    speechSynthesis.speak(utterance);
}

// button functionality to go back to movies and save progress
async function backToMovies() {
    const videoPlayer = document.getElementById('videoPlayer');

    // Prevent saving if no movie is currently playing
    if (!currentMovieId || !currentUserId || !videoPlayer.duration) {
        document.getElementById('playerSection').style.display = 'none';
        document.getElementById('moviesSection').style.display = 'block';
        document.getElementById('userMoviesSection').style.display = 'block';
        videoPlayer.pause();
        videoPlayer.src = '';
        return;
    }

    const progress = (videoPlayer.currentTime / videoPlayer.duration) * 100;
    
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: 'saveProgress',
                userId: currentUserId,
                movieId: currentMovieId,
                progress: progress,
                timestamp: new Date().toISOString()
            })
        });
        
        if(!response.ok) {
            throw new Error('Network response was not ok');
        }

        alert('Progress saved successfully!');
    } catch (error) {
        alert('Error saving progress: ' + error.message);
        console.error('Error saving the progress: ' + error);
    }

    document.getElementById('playerSection').style.display = 'none';
    document.getElementById('moviesSection').style.display = 'block';
    document.getElementById('userMoviesSection').style.display = 'block';
    
    videoPlayer.pause();
    videoPlayer.src = '';
    
    loadAllProgress();
}

//saving video progress logic
async function saveProgress() {
    if (!isAuthenticated) {
        alert('Please login first');
        return;
    }
    
    const videoPlayer = document.getElementById('videoPlayer');
    const progress = (videoPlayer.currentTime / videoPlayer.duration) * 100;
    
    try {
        await fetch(API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                action: 'saveProgress',
                userId: currentUserId,
                movieId: currentMovieId,
                progress: progress,
                timestamp: new Date().toISOString()
            })
        });
        
        alert('Progress saved successfully!');
    } catch (error) {
        alert('Error saving progress: ' + error.message);
        console.error(error);
    }
}

//-------------------------------- USER UPLOADED MOVIES -------------------------------
function openUploadPopup() {
    document.getElementById("uploadModal").style.display = "block";
}
function closeUploadPopup() {
    document.getElementById("uploadModal").style.display = "none";
}

async function uploadMovieFromPopup() {
    const file = document.getElementById("popupFileInput").files[0];

    if (!file) {
        alert("Select a file first");
        return;
    }

    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                action: "requestUploadUrl",
                userId: currentUserId,
                fileName: file.name
            })
        });

        const result = await response.json();
        const data = result.body ? JSON.parse(result.body) : result;

        await fetch(data.uploadUrl, {
            method: "PUT",
            headers: { "Content-Type": "video/mp4" },
            body: file
        });

        closeUploadPopup();
        getUserMovies();
    } catch (err) {
        alert("Upload failed");
    }
}

async function getUserMovies() {
    try {
        const response = await fetch(API_URL, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                action: "listUserMovies",
                userId: currentUserId
            })
        });

        const result = await response.json();
        const data = result.body ? JSON.parse(result.body) : result;

        const grid = document.getElementById("userMovieGrid");
        grid.innerHTML = "";

        if (!data.movies || data.movies.length === 0) {
            grid.innerHTML = "<p>No uploaded movies yet.</p>";
            return;
        }

        data.movies.forEach(movie => {
            const el = document.createElement("div");
            el.className = "movie-card";
            el.onclick = () => playUserMovie(movie.videoUrl, movie.movieId);

            el.innerHTML = `
                <div class="movie-thumbnail">
                    <h3>${movie.movieId}</h3>
                </div>
                <p>Your Uploaded Movie</p>
            `;

            grid.appendChild(el);
        });

    } catch (err) {
        console.error("User movie load error:", err);
    }
}

function playUserMovie(videoUrl, movieId) {
    currentMovieId = movieId;

    // Hide home sections
    document.getElementById('moviesSection').style.display = 'none';
    document.getElementById('userMoviesSection').style.display = 'none'; // <-- hide user uploads
    document.getElementById('playerSection').style.display = 'block';
    
    document.getElementById('currentMovie').textContent = `Now Playing: ${movieId}`;

    const videoPlayer = document.getElementById('videoPlayer');
    videoPlayer.src = videoUrl;
    videoPlayer.play();
}




//dev bypass button DELETE AFTER TESTING
function debugBypassLogin() {
    isAuthenticated = true;
    currentUser = "devUser";
    currentUserId = "dev-user-123";

    document.getElementById('userDisplay').textContent = currentUser;
    document.getElementById('loginSection').style.display = 'none';
    document.getElementById('moviesSection').style.display = 'block';
    document.getElementById('userMoviesSection').style.display = 'block';

    loadAllProgress();
    loadUserVideos(); // New function in your updated code
}
