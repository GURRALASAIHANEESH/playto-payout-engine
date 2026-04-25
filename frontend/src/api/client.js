const BASE_URL = import.meta.env.VITE_API_URL || "/api/v1";

async function request(path, options = {}) {
    const url = `${BASE_URL}${path}`;
    const { headers: customHeaders, ...restOptions } = options;

    const res = await fetch(url, {
        headers: {
            "Content-Type": "application/json",
            ...customHeaders,
        },
        ...restOptions,
    });

    const data = await res.json();

    if (!res.ok) {
        const error = new Error(data.detail || data.error || "Request failed");
        error.status = res.status;
        error.data = data;
        throw error;
    }

    return data;
}

export function getBalance(merchantId) {
    return request(`/merchants/${merchantId}/balance/`);
}

export function getLedger(merchantId) {
    return request(`/merchants/${merchantId}/ledger/`);
}

export function getPayouts(merchantId) {
    return request(`/merchants/${merchantId}/payouts/`);
}

export function getPayout(payoutId, merchantId) {
    return request(`/payouts/${payoutId}/`, {
        headers: { "X-Merchant-ID": String(merchantId) },
    });
}

export function createPayout(merchantId, idempotencyKey, body) {
    return request("/payouts/", {
        method: "POST",
        headers: {
            "X-Merchant-ID": String(merchantId),
            "Idempotency-Key": idempotencyKey,
        },
        body: JSON.stringify(body),
    });
}