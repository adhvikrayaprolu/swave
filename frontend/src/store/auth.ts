import {create} from 'zustand';
import {persist} from 'zustand/middleware';
import {api,clearTokens} from '@/api/client';
import type {User,LoginRequest,RegisterRequest} from '@/api/types';
interface AuthState {
  user:User|null; isAuthenticated:boolean; isLoading:boolean; error:string|null; isDemoMode:boolean;
  login:(data:LoginRequest)=>Promise<void>;register:(data:RegisterRequest)=>Promise<void>;
  logout:()=>Promise<void>;loadProfile:()=>Promise<void>;enterDemoMode:()=>void;clearError:()=>void;setLoading:(value:boolean)=>void;
}
export const useAuthStore=create<AuthState>()(persist((set,get)=>({
  user:null,isAuthenticated:false,isLoading:false,error:null,isDemoMode:false,
  login:async(data)=>{set({isLoading:true,error:null});try{const result=await api.auth.login(data);set({user:result.user,isAuthenticated:true,isDemoMode:false,isLoading:false});}catch(error){set({error:error instanceof Error?error.message:'Login failed',isLoading:false});throw error;}},
  register:async(data)=>{set({isLoading:true,error:null});try{const result=await api.auth.register(data);set({user:result.user,isAuthenticated:true,isDemoMode:false,isLoading:false});}catch(error){set({error:error instanceof Error?error.message:'Registration failed',isLoading:false});throw error;}},
  logout:async()=>{try{if(!get().isDemoMode)await api.auth.logout();}finally{clearTokens();set({user:null,isAuthenticated:false,isDemoMode:false,isLoading:false});}},
  loadProfile:async()=>{if(get().isDemoMode)return;set({isLoading:true});try{const user=await api.auth.getProfile();set({user,isAuthenticated:true,isLoading:false});}catch{set({user:null,isAuthenticated:false,isLoading:false});}},
  enterDemoMode:()=>{clearTokens();set({user:null,isAuthenticated:true,isDemoMode:true,isLoading:false,error:null});},
  clearError:()=>set({error:null}),setLoading:(isLoading)=>set({isLoading}),
}),{name:'auth-storage',partialize:state=>({user:state.user,isAuthenticated:state.isAuthenticated,isDemoMode:state.isDemoMode})}));
