/* Temporary stability guard for the guided-home loader.
   The loader previously observed MAIN attributes and, inside its callback,
   wrote the same hidden/class attributes again. Chromium can keep scheduling
   that observer indefinitely, freezing the UI while the cursor remains a hand.
   Block only that exact observer; all other MutationObservers keep working. */
(function(){
  const NativeMutationObserver=window.MutationObserver;
  if(!NativeMutationObserver||window.__perspectivesMutationGuard)return;
  window.__perspectivesMutationGuard=true;

  window.MutationObserver=class MutationObserverGuard{
    constructor(callback){
      this._native=new NativeMutationObserver(callback);
    }
    observe(target,options){
      const filters=(options&&options.attributeFilter)||[];
      const isProblemObserver=target&&target.tagName==='MAIN'&&options&&options.subtree===true&&options.attributes===true&&filters.includes('hidden')&&filters.includes('style')&&filters.includes('class');
      if(isProblemObserver){
        console.info('Perspectives Emploi: recursive MAIN observer disabled');
        return;
      }
      return this._native.observe(target,options);
    }
    disconnect(){return this._native.disconnect();}
    takeRecords(){return this._native.takeRecords();}
  };
})();