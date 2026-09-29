import {useState,useEffect} from 'react';
import {Navigate} from 'react-router-dom';
import {useAuthStore} from '@/store/auth';
import {Button} from '@/components/ui/button';
import {LoginForm} from '@/components/auth/LoginForm';
import {RegisterForm} from '@/components/auth/RegisterForm';
export const AuthScreen=()=>{
  const [mode,setMode]=useState<'login'|'register'>('login');
  const {loadProfile,isAuthenticated,isDemoMode,enterDemoMode}=useAuthStore();
  useEffect(()=>{void loadProfile();},[loadProfile]);
  if(isAuthenticated||isDemoMode)return <Navigate to="/" replace/>;
  return <main className="min-h-screen bg-background p-6 flex flex-col items-center justify-center gap-6">
    <header className="text-center"><h1 className="text-4xl font-bold">Swave</h1><p>Discover music, save likes, build a daily playlist.</p></header>
    {mode==='login'?<LoginForm onSwitchToRegister={()=>setMode('register')}/>:<RegisterForm onSwitchToLogin={()=>setMode('login')}/>}
    <Button variant="outline" onClick={enterDemoMode}>Try Demo Mode</Button>
    <p className="text-sm text-muted-foreground">Demo uses sample tracks and simulated saves. Register for persistent likes.</p>
  </main>;
};
