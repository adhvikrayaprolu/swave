import * as React from 'react';
import * as Primitive from '@radix-ui/react-dialog';
import {X} from 'lucide-react';
export const Dialog=Primitive.Root;
export const DialogTitle=Primitive.Title;
export const DialogDescription=Primitive.Description;
export const DialogContent=({children}:React.PropsWithChildren)=> <Primitive.Portal>
  <Primitive.Overlay className="fixed inset-0 bg-black/60 z-50"/>
  <Primitive.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-[calc(100%-2rem)] max-w-md rounded-2xl bg-card p-6 border shadow-lg">
    {children}<Primitive.Close className="absolute right-3 top-3" aria-label="Close playlist"><X/></Primitive.Close>
  </Primitive.Content>
</Primitive.Portal>;
