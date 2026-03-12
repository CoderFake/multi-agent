import { getIdToken } from "./auth-client";

export async function fetchWithAuth(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
    let response = await fetch(input, init);

    if (response.status === 401) {
        try {
            const newToken = await getIdToken(true);

            if (newToken) {
                const syncResponse = await fetch("/api/auth/session", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify({ token: newToken }),
                });

                if (syncResponse.ok) {
                    response = await fetch(input, init);
                } else {
                    console.error("Token sync with server failed upon refresh");
                }
            } else {
                console.error("No active user to refresh token");
            }
        } catch (error) {
            console.error("Error during token refresh:", error);
        }
    }

    return response;
}
