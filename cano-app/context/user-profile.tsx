import { createContext, useContext, useState, useCallback, ReactNode } from 'react';
import { getUserProfile, UserProfileDto } from '@/api/users';

interface UserProfileContextValue {
  profile: UserProfileDto | null;
  loadProfile: () => Promise<void>;
  clearProfile: () => void;
}

const UserProfileContext = createContext<UserProfileContextValue>({
  profile: null,
  loadProfile: async () => {},
  clearProfile: () => {},
});

export function UserProfileProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [profile, setProfile] = useState<UserProfileDto | null>(null);

  const loadProfile = useCallback(async () => {
    try {
      const p = await getUserProfile();
      setProfile(p);
    } catch {
      setProfile(null);
    }
  }, []);

  const clearProfile = useCallback(() => setProfile(null), []);

  return (
    <UserProfileContext.Provider value={{ profile, loadProfile, clearProfile }}>
      {children}
    </UserProfileContext.Provider>
  );
}

export function useUserProfile() {
  return useContext(UserProfileContext);
}
