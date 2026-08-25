import { db } from './firebase';
import { collection, doc, setDoc, getDoc, updateDoc, serverTimestamp } from 'firebase/firestore';
import type { User, UserProfile } from '@/api/types';

// Firestore collections
const USERS_COLLECTION = 'users';
const PROFILES_COLLECTION = 'profiles';

export const firestoreService = {
  // Create or update user in Firestore
  async saveUser(userId: string, userData: Partial<User>): Promise<void> {
    try {
      const userRef = doc(db, USERS_COLLECTION, userId);
      await setDoc(userRef, {
        ...userData,
        updatedAt: serverTimestamp(),
      }, { merge: true });
    } catch (error) {
      console.error('Error saving user to Firestore:', error);
      throw error;
    }
  },

  // Get user from Firestore
  async getUser(userId: string): Promise<User | null> {
    try {
      const userRef = doc(db, USERS_COLLECTION, userId);
      const userSnap = await getDoc(userRef);
      
      if (userSnap.exists()) {
        return userSnap.data() as User;
      }
      return null;
    } catch (error) {
      console.error('Error getting user from Firestore:', error);
      throw error;
    }
  },

  // Save user profile
  async saveProfile(userId: string, profileData: UserProfile): Promise<void> {
    try {
      const profileRef = doc(db, PROFILES_COLLECTION, userId);
      await setDoc(profileRef, {
        ...profileData,
        updatedAt: serverTimestamp(),
      });
    } catch (error) {
      console.error('Error saving profile to Firestore:', error);
      throw error;
    }
  },

  // Get user profile
  async getProfile(userId: string): Promise<UserProfile | null> {
    try {
      const profileRef = doc(db, PROFILES_COLLECTION, userId);
      const profileSnap = await getDoc(profileRef);
      
      if (profileSnap.exists()) {
        return profileSnap.data() as UserProfile;
      }
      return null;
    } catch (error) {
      console.error('Error getting profile from Firestore:', error);
      throw error;
    }
  },
};

