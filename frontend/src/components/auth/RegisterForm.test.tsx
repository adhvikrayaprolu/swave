import React from 'react';
import {afterEach,expect,it,vi} from 'vitest';
import {render,screen,cleanup} from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {RegisterForm} from './RegisterForm';
import {useAuthStore} from '@/store/auth';
afterEach(cleanup);
it('reports mismatched passwords and does not register',async()=>{
 const register=vi.fn();useAuthStore.setState({register,error:null,isLoading:false});
 render(<RegisterForm onSwitchToLogin={()=>{}}/>);const user=userEvent.setup();
 await user.type(screen.getByLabelText('Username'),'listener');await user.type(screen.getByLabelText('Email'),'listener@example.test');
 await user.type(screen.getByLabelText('Password',{exact:true}),'password-one');await user.type(screen.getByLabelText('Confirm Password'),'password-two');
 await user.click(screen.getByRole('button',{name:'Create Account'}));
 expect(screen.getByText('Passwords do not match')).toBeTruthy();expect(register).not.toHaveBeenCalled();
});
