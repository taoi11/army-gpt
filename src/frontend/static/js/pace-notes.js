// Constants
const MAX_RESPONSES = 5;  // Maximum number of response cards to keep

// Track active request
let activeReader = null;
let abortController = null;

// Function to cleanup any ongoing requests
async function cleanupActiveRequest() {
    try {
        if (activeReader) {
            await activeReader.cancel();
            activeReader = null;
        }
    } catch (e) {
        console.log('Error cleaning up reader:', e);
    }

    try {
        if (abortController) {
            abortController.abort();
            abortController = null;
        }
    } catch (e) {
        console.log('Error aborting controller:', e);
    }

    // Force cleanup of any hanging connections
    try {
        await fetch('/llm/pace-notes/cancel', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        }).catch(() => {});  // Ignore any errors here
    } catch (e) {
        // Ignore cleanup request errors
    }
}

// Add event listeners for cleanup
function setupCleanupListeners() {
    // Add event listener for page visibility change
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'hidden') {
            cleanupActiveRequest();
        }
    });

    // Add event listener for page unload/refresh - using 'pagehide' for better browser support
    window.addEventListener('pagehide', () => {
        cleanupActiveRequest();
        // Force immediate cleanup
        if (navigator.sendBeacon) {
            navigator.sendBeacon('/llm/pace-notes/cancel');
        }
    });
}

// Handle form submission
async function handleSubmit(e) {
    e.preventDefault();
    
    // Cleanup any existing request
    await cleanupActiveRequest();
    
    // Get form data
    const userInput = document.getElementById('userInput').value.trim();
    if (!userInput) return;

    // Reset textarea height only
    document.getElementById('userInput').style.height = 'auto';

    // Create new response box
    const responseBox = document.createElement('div');
    responseBox.className = 'bg-white rounded-lg shadow-md p-6 response-container';
    responseBox.innerHTML = `
        <div class="flex justify-between items-start">
            <p class="text-gray-800 whitespace-pre-line thinking">Thinking</p>
            <button
                onclick="copyToClipboard(this.parentElement.querySelector('p').textContent)"
                class="ml-4 text-blue-600 hover:text-blue-800 focus:outline-none hidden"
            >
                Copy
            </button>
        </div>
    `;

    // Add to container
    const resultsContainer = document.getElementById('resultsContainer');
    resultsContainer.insertBefore(responseBox, resultsContainer.firstChild);
    const responseParagraph = responseBox.querySelector('p');
    const copyButton = responseBox.querySelector('button');

    try {
        // Setup abort controller for the fetch request
        abortController = new AbortController();

        // Setup EventSource for streaming with a timeout
        const timeoutId = setTimeout(() => {
            if (abortController) {
                abortController.abort();
            }
        }, 30000); // 30 second timeout

        const response = await fetch('/llm/pace-notes/generate', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                content: userInput,
                temperature: 0.1,
                stream: true
            }),
            signal: abortController.signal
        });

        clearTimeout(timeoutId); // Clear timeout if request succeeds

        if (!response.ok) {
            if (response.status === 429) {
                const errorData = await response.json();
                const hourlyRemaining = errorData.error.details.hourly_remaining;
                const dailyRemaining = errorData.error.details.daily_remaining;
                
                responseBox.innerHTML = `
                    <div class="p-4 bg-amber-100 text-amber-800 rounded-lg">
                        <p class="font-semibold mb-2">Rate Limit Reached</p>
                        <p>You've reached the request limit. Please wait before trying again.</p>
                        <p class="mt-2 text-sm">
                            Remaining requests:<br>
                            Hourly: ${hourlyRemaining}<br>
                            Daily: ${dailyRemaining}
                        </p>
                    </div>
                `;
                return;
            }
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        // Handle streaming response
        const reader = response.body.getReader();
        activeReader = reader;
        const decoder = new TextDecoder();
        let fullText = '';
        let firstChunkReceived = false;

        while (true) {
            const { value, done } = await reader.read();
            if (done) {
                activeReader = null;
                break;
            }

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');

            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        if (data.error) {
                            throw new Error(data.error);
                        }
                        if (data.note) {
                            if (!firstChunkReceived) {
                                // Remove thinking animation and show copy button on first chunk
                                responseParagraph.classList.remove('thinking');
                                copyButton.classList.remove('hidden');
                                firstChunkReceived = true;
                            }
                            fullText += data.note;
                            responseParagraph.textContent = fullText;
                        }
                    } catch (e) {
                        console.error('Error parsing SSE data:', e);
                    }
                }
            }
        }

        // Update rate limits after response is complete
        try {
            const limitsResponse = await fetch('/api/limits');
            const limitsData = await limitsResponse.json();
            updateRateLimits(limitsData);
        } catch (error) {
            console.error('Error updating rate limits:', error);
        }

        // Remove old responses if we have more than MAX_RESPONSES
        const responses = resultsContainer.getElementsByClassName('response-container');
        while (responses.length > MAX_RESPONSES) {
            resultsContainer.removeChild(responses[responses.length - 1]);
        }

        // Scroll to new response
        responseBox.scrollIntoView({ behavior: 'smooth', block: 'end' });

    } catch (error) {
        if (error.name === 'AbortError') {
            console.log('Request was aborted');
        } else {
            console.error('Error generating note:', error);
            responseBox.innerHTML = `
                <div class="p-4 bg-red-100 text-red-700 rounded-lg">
                    Error: Failed to get response. Please try again.
                </div>
            `;
        }
    } finally {
        // Clear active reader if it wasn't already cleared
        if (activeReader) {
            try {
                await activeReader.cancel();
            } catch (e) {
                // Ignore cancel errors
            }
            activeReader = null;
        }
        abortController = null;
    }
}

// Initialize pace notes functionality
function initializePaceNotes() {
    // Setup form handler
    document.getElementById('paceNoteForm').addEventListener('submit', handleSubmit);

    // Setup cleanup listeners
    setupCleanupListeners();

    // Initialize common features
    initializeCommon();
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializePaceNotes); 