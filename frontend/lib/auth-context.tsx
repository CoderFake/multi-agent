'use client';

import {
    createContext,
    useContext,
    useEffect,
    useState,
    ReactNode,
} from 'react';
import {
    User,
    onIdTokenChanged,
    signOut as firebaseSignOut,
} from 'firebase/auth';
import { auth } from '@/lib/firebase';
import { useCallback, useRef } from 'react';

interface AuthContextValue {
    user: User | null;
    loading: boolean;
    getIdToken: (forceRefresh?: boolean) => Promise<string | null>;
    signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue>({
    user: null,
    loading: true,
    getIdToken: async () => null,
    signOut: async () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [loading, setLoading] = useState(true);
    const userRef = useRef<User | null>(null);

    useEffect(() => {
        const unsubscribe = onIdTokenChanged(auth, (firebaseUser) => {
            userRef.current = firebaseUser;
            setUser(firebaseUser);
            setLoading(false);
        });
        return unsubscribe;
    }, []);

    const getIdToken = useCallback(async (forceRefresh = false): Promise<string | null> => {
        const u = userRef.current;
        if (!u) return null;
        try {
            return await u.getIdToken(forceRefresh);
        } catch {
            return null;
        }
    }, []);

    const signOut = useCallback(async () => {
        await firebaseSignOut(auth);
    }, []);

    return (
        <AuthContext.Provider value={{ user, loading, getIdToken, signOut }}>
            {children}
        </AuthContext.Provider>
    );
}

export const useAuth = () => useContext(AuthContext);
