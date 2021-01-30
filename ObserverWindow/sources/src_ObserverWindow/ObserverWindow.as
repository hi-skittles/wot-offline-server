
package
{
	import flash.events.MouseEvent;
	import net.wg.infrastructure.base.AbstractWindowView;
	import net.wg.gui.components.controls.TextFieldShort;
	import net.wg.gui.components.controls.SoundButton;
	import net.wg.gui.components.controls.IconText;
	import net.wg.gui.components.controls.UILoaderAlt;
	
	public class ObserverWindow extends AbstractWindowView
	{		
		public var showSelectMap:Function = null;
		public var startLoading:Function = null;
		
		override protected function onPopulate() : void
		{
			super.onPopulate();
			this.width = 180;
			this.height = 120;
			this.window.title = "Offline Map Viewer";
			
			this.selectMapButton = App.utils.classFactory.getComponent("ButtonNormal", SoundButton);
			this.selectMapButton.width = 170;
			this.selectMapButton.height = 25;
			this.selectMapButton.x = 5;
			this.selectMapButton.y = 5;
			this.selectMapButton.label = "Select Map";
			
			this.arenaNameField = App.utils.classFactory.getComponent("TextFieldShort", TextFieldShort);
			this.arenaNameField.width = 170;
			this.arenaNameField.x = 5;
			this.arenaNameField.y = 35;
			this.arenaNameField.label = "Unselected";
			this.arenaNameField.validateNow();
				
			this.startLoadingButton = App.utils.classFactory.getComponent("ButtonNormal", SoundButton);
			this.startLoadingButton.width = 170;
			this.startLoadingButton.height = 25;
			this.startLoadingButton.x = 5;
			this.startLoadingButton.y = 60;
			this.startLoadingButton.label = "Start Loading";
			this.startLoadingButton.enabled = false;
			
			this.selectMapButton.addEventListener(MouseEvent.CLICK, this.handleSelectMapClick);
			this.startLoadingButton.addEventListener(MouseEvent.CLICK, this.handleLoadingClick);	
			
			this.addChild(this.selectMapButton);
			this.addChild(this.arenaNameField);
			this.addChild(this.startLoadingButton);
		}
		
		public function as_setArena(str:String, str2:String) : void
		{
			this.arenaNameField.label = str;
			this.arenaNameField.validateNow();
		}
	
		public function as_setLoadingEnabled(bool:Boolean) : void
		{
			this.startLoadingButton.enabled = bool;
		}
		
		public function handleLoadingClick(event:MouseEvent) : void
		{
			this.startLoading();
		}
		
		public function handleSelectMapClick(event:MouseEvent) : void
		{
			this.showSelectMap();
		}
		
		public var selectMapButton:SoundButton;
		public var startLoadingButton:SoundButton;
		public var arenaNameField:TextFieldShort;
   }
}