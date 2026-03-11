export async function fetchWithAuth(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
    let response = await fetch(input, init);

    // If the request fails with 401 Unauthorized, attempt to refresh the token
    if (response.status === 401) {
        try {
            const refreshResponse = await fetch("/api/auth/refresh", {
                method: "POST",
            });

            if (refreshResponse.ok) {
                // Token successfully refreshed, retry the original request
                response = await fetch(input, init);
            } else {
                // If refresh fails, we might need to redirect to login or handle session expiration
                console.error("Token refresh failed");
            }
        } catch (error) {
            console.error("Error during token refresh:", error);
        }
    }

    return response;
}
